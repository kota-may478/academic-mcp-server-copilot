from __future__ import annotations

import asyncio
import gzip
import io
import re
import tarfile
import time
import zipfile
from pathlib import PurePosixPath
from typing import Any

import feedparser
import httpx
from pypdf import PdfReader

from academic_mcp_server.common.cache import TTLCache
from academic_mcp_server.common.config import AppConfig
from academic_mcp_server.common.models import ArxivFullTextResponse, DocumentArtifact, Paper, PaperSearchResponse
from academic_mcp_server.common.normalize import coerce_int, normalize_arxiv_entry, normalize_limit


class ArxivConnector:
    """Async client for arXiv Atom API with serialized rate limiting."""

    _MAX_SOURCE_MEMBER_BYTES = 10_000_000
    _MAX_SOURCE_TOTAL_BYTES = 50_000_000

    def __init__(self, config: AppConfig) -> None:
        self._default_limit = config.default_limit
        self._cache: TTLCache[Any] = TTLCache(config.cache_ttl_seconds)
        self._client = httpx.AsyncClient(
            base_url="https://export.arxiv.org",
            headers={"Accept": "application/atom+xml"},
            limits=httpx.Limits(max_connections=1, max_keepalive_connections=1),
            timeout=config.request_timeout_seconds,
        )
        self._download_client = httpx.AsyncClient(
            base_url="https://arxiv.org",
            headers={"Accept": "*/*"},
            limits=httpx.Limits(max_connections=1, max_keepalive_connections=1),
            timeout=config.request_timeout_seconds,
            follow_redirects=True,
        )
        self._request_lock = asyncio.Lock()
        self._last_request_finished_at = 0.0
        self._minimum_interval_seconds = 3.0

    async def aclose(self) -> None:
        await asyncio.gather(
            self._client.aclose(),
            self._download_client.aclose(),
        )
        self._cache.clear()

    async def search(self, query: str, limit: int | None = None) -> PaperSearchResponse:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("query must not be empty.")

        normalized_limit = normalize_limit(limit, default=self._default_limit, maximum=20)
        cache_key = f"search:{normalized_query}:{normalized_limit}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        feed = await self._get_feed(
            params={
                "search_query": f"all:{normalized_query}",
                "start": 0,
                "max_results": normalized_limit,
                "sortBy": "relevance",
                "sortOrder": "descending",
            }
        )
        result = PaperSearchResponse(
            source="arxiv",
            query=normalized_query,
            limit=normalized_limit,
            total=coerce_int(feed.feed.get("opensearch_totalresults")),
            items=[normalize_arxiv_entry(entry) for entry in feed.entries],
        )
        self._cache.set(cache_key, result)
        return result

    async def get_paper(self, arxiv_id: str) -> Paper:
        normalized_identifier = self._normalize_identifier(arxiv_id)
        cache_key = f"paper:{normalized_identifier}"
        cached = self._cache.get(cache_key)
        if isinstance(cached, Paper):
            return cached

        feed = await self._get_feed(params={"id_list": normalized_identifier})
        if not feed.entries:
            raise RuntimeError(f"arXiv paper '{normalized_identifier}' was not found.")

        result = normalize_arxiv_entry(feed.entries[0])
        self._cache.set(cache_key, result)
        return result

    async def analyze_full_text(
        self,
        arxiv_id: str,
        *,
        prefer: str = "source",
        max_characters: int = 200_000,
    ) -> ArxivFullTextResponse:
        normalized_identifier = self._normalize_identifier(arxiv_id)
        normalized_preference = self._normalize_extraction_preference(prefer)
        normalized_max_characters = self._normalize_max_characters(max_characters)
        cache_key = (
            f"fulltext:{normalized_identifier}:{normalized_preference}:"
            f"{normalized_max_characters or 'all'}"
        )
        cached = self._cache.get(cache_key)
        if isinstance(cached, ArxivFullTextResponse):
            return cached

        paper = await self.get_paper(arxiv_id=normalized_identifier)
        notes: list[str] = []
        extraction_order = ["source", "pdf"] if normalized_preference == "source" else ["pdf", "source"]

        for extraction_method in extraction_order:
            try:
                if extraction_method == "source":
                    result = await self._analyze_from_source(
                        paper=paper,
                        normalized_identifier=normalized_identifier,
                        max_characters=normalized_max_characters,
                    )
                else:
                    result = await self._analyze_from_pdf(
                        paper=paper,
                        normalized_identifier=normalized_identifier,
                        max_characters=normalized_max_characters,
                    )

                if notes:
                    result = result.model_copy(update={"notes": [*notes, *result.notes]})

                self._cache.set(cache_key, result)
                return result
            except RuntimeError as exc:
                notes.append(f"{extraction_method}: {exc}")

        raise RuntimeError(
            f"arXiv full-text extraction failed for '{normalized_identifier}'. "
            + " ".join(notes)
        )

    async def _get_feed(self, *, params: dict[str, Any]) -> feedparser.FeedParserDict:
        response = await self._get_response(
            self._client,
            "/api/query",
            params=params,
            error_label="arXiv",
        )

        feed = feedparser.parse(response.text)
        if getattr(feed, "bozo", 0):
            bozo_exception = getattr(feed, "bozo_exception", None)
            if bozo_exception is not None:
                raise RuntimeError(f"arXiv feed parsing failed: {bozo_exception}")

        return feed

    async def _analyze_from_source(
        self,
        *,
        paper: Paper,
        normalized_identifier: str,
        max_characters: int | None,
    ) -> ArxivFullTextResponse:
        source_path = f"/src/{normalized_identifier}"
        response = await self._get_response(
            self._download_client,
            source_path,
            error_label="arXiv source download",
        )
        payload = response.content
        payload_kind = self._detect_payload_kind(payload, content_type=response.headers.get("Content-Type"))
        if payload_kind == "pdf":
            raise RuntimeError("source endpoint returned PDF content instead of source files")

        source_files, bundle_format = self._extract_source_files(
            payload,
            normalized_identifier=normalized_identifier,
        )
        text_documents = self._collect_text_documents(source_files)
        if not text_documents:
            raise RuntimeError("source archive did not contain readable TeX-like documents")

        combined_source, used_paths, main_document = self._assemble_source_text(text_documents)
        full_text = self._latex_to_text(combined_source)
        if not full_text.strip():
            raise RuntimeError("source files were downloaded, but no readable text could be extracted")

        full_text_char_count = len(full_text)
        full_text, was_truncated = self._truncate_text(full_text, max_characters)
        figure_items, table_items = self._extract_artifacts(
            text_documents,
            used_paths=used_paths,
        )
        notes: list[str] = []
        if was_truncated:
            notes.append(
                f"full_text was truncated to {max_characters} characters; set max_characters=0 to disable truncation"
            )

        return ArxivFullTextResponse(
            source="arxiv",
            source_id=normalized_identifier,
            extraction_method="source",
            content_url=f"https://arxiv.org{source_path}",
            paper=paper,
            full_text=full_text,
            full_text_char_count=full_text_char_count,
            full_text_truncated=was_truncated,
            figure_items=figure_items,
            table_items=table_items,
            notes=notes,
            extraction_metadata={
                "source_bundle_format": bundle_format,
                "main_document": main_document,
                "used_documents": used_paths,
                "archive_file_count": len(source_files),
                "text_document_count": len(text_documents),
            },
        )

    async def _analyze_from_pdf(
        self,
        *,
        paper: Paper,
        normalized_identifier: str,
        max_characters: int | None,
    ) -> ArxivFullTextResponse:
        pdf_path = f"/pdf/{normalized_identifier}.pdf"
        response = await self._get_response(
            self._download_client,
            pdf_path,
            error_label="arXiv PDF download",
        )
        reader = PdfReader(io.BytesIO(response.content))
        page_texts = [page.extract_text() or "" for page in reader.pages]
        full_text = "\n\n".join(text.strip() for text in page_texts if text.strip())
        if not full_text:
            raise RuntimeError("PDF was downloaded, but no readable text could be extracted")

        full_text_char_count = len(full_text)
        full_text, was_truncated = self._truncate_text(full_text, max_characters)
        notes = ["figure/table extraction is only available when source files can be parsed"]
        if was_truncated:
            notes.append(
                f"full_text was truncated to {max_characters} characters; set max_characters=0 to disable truncation"
            )

        return ArxivFullTextResponse(
            source="arxiv",
            source_id=normalized_identifier,
            extraction_method="pdf",
            content_url=f"https://arxiv.org{pdf_path}",
            paper=paper,
            full_text=full_text,
            full_text_char_count=full_text_char_count,
            full_text_truncated=was_truncated,
            figure_items=[],
            table_items=[],
            notes=notes,
            extraction_metadata={
                "page_count": len(reader.pages),
                "pdf_size_bytes": len(response.content),
            },
        )

    async def _get_response(
        self,
        client: httpx.AsyncClient,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        error_label: str,
    ) -> httpx.Response:
        async with self._request_lock:
            wait_seconds = self._minimum_interval_seconds - (
                time.monotonic() - self._last_request_finished_at
            )
            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)

            try:
                response = await client.get(path, params=params)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise RuntimeError(
                    f"{error_label} returned HTTP {exc.response.status_code}."
                ) from exc
            except httpx.HTTPError as exc:
                raise RuntimeError(f"{error_label} request failed: {exc}") from exc
            finally:
                self._last_request_finished_at = time.monotonic()

        return response

    def _extract_source_files(
        self,
        payload: bytes,
        *,
        normalized_identifier: str,
    ) -> tuple[dict[str, bytes], str]:
        payload_kind = self._detect_payload_kind(payload)
        if payload_kind == "tar":
            return self._read_tar_archive(payload), "tar"
        if payload_kind == "zip":
            return self._read_zip_archive(payload), "zip"
        if payload_kind == "gzip":
            decompressed = gzip.decompress(payload)
            inner_kind = self._detect_payload_kind(decompressed)
            if inner_kind == "tar":
                return self._read_tar_archive(decompressed), "tar.gz"
            if inner_kind == "zip":
                return self._read_zip_archive(decompressed), "zip.gz"
            if inner_kind == "pdf":
                raise RuntimeError("source archive decompressed into PDF content")
            if inner_kind == "text":
                return {f"{normalized_identifier}.tex": decompressed}, "gz"
            raise RuntimeError("source archive used an unsupported gzip payload")
        if payload_kind == "text":
            return {f"{normalized_identifier}.tex": payload}, "text"

        raise RuntimeError("source download used an unsupported archive format")

    def _read_tar_archive(self, payload: bytes) -> dict[str, bytes]:
        extracted_files: dict[str, bytes] = {}
        total_bytes = 0
        with tarfile.open(fileobj=io.BytesIO(payload), mode="r:*") as archive:
            for member in archive.getmembers():
                if not member.isfile() or member.size <= 0:
                    continue
                if member.size > self._MAX_SOURCE_MEMBER_BYTES:
                    continue

                normalized_path = self._normalize_archive_path(member.name)
                if normalized_path is None:
                    continue

                extracted = archive.extractfile(member)
                if extracted is None:
                    continue

                data = extracted.read(self._MAX_SOURCE_MEMBER_BYTES + 1)
                if len(data) > self._MAX_SOURCE_MEMBER_BYTES:
                    continue

                total_bytes += len(data)
                if total_bytes > self._MAX_SOURCE_TOTAL_BYTES:
                    break

                extracted_files[normalized_path] = data

        if not extracted_files:
            raise RuntimeError("source archive was empty or only contained unsupported files")

        return extracted_files

    def _read_zip_archive(self, payload: bytes) -> dict[str, bytes]:
        extracted_files: dict[str, bytes] = {}
        total_bytes = 0
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            for member in archive.infolist():
                if member.is_dir() or member.file_size <= 0:
                    continue
                if member.file_size > self._MAX_SOURCE_MEMBER_BYTES:
                    continue

                normalized_path = self._normalize_archive_path(member.filename)
                if normalized_path is None:
                    continue

                data = archive.read(member)
                total_bytes += len(data)
                if total_bytes > self._MAX_SOURCE_TOTAL_BYTES:
                    break

                extracted_files[normalized_path] = data

        if not extracted_files:
            raise RuntimeError("source archive was empty or only contained unsupported files")

        return extracted_files

    @staticmethod
    def _normalize_archive_path(path: str) -> str | None:
        normalized_parts = [
            part
            for part in PurePosixPath(path.replace("\\", "/")).parts
            if part not in {"", ".", ".."}
        ]
        if not normalized_parts:
            return None
        return PurePosixPath(*normalized_parts).as_posix()

    def _collect_text_documents(self, source_files: dict[str, bytes]) -> dict[str, str]:
        documents: dict[str, str] = {}
        for path, payload in source_files.items():
            decoded = self._decode_text_payload(payload)
            if decoded is None:
                continue
            if self._looks_like_tex_document(path, decoded):
                documents[path] = decoded
        return documents

    @staticmethod
    def _decode_text_payload(payload: bytes) -> str | None:
        for encoding in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                return payload.decode(encoding)
            except UnicodeDecodeError:
                continue
        return None

    @staticmethod
    def _looks_like_tex_document(path: str, text: str) -> bool:
        suffix = PurePosixPath(path).suffix.lower()
        if suffix in {".tex", ".ltx", ".txt"}:
            return True
        if suffix in {".sty", ".cls", ".bst", ".bib", ".bbl", ".png", ".jpg", ".jpeg", ".pdf", ".eps"}:
            return False

        return any(
            marker in text
            for marker in (
                "\\begin{document}",
                "\\documentclass",
                "\\section",
                "\\subsection",
                "\\title{",
                "\\begin{abstract}",
            )
        )

    def _assemble_source_text(self, documents: dict[str, str]) -> tuple[str, list[str], str]:
        main_document = self._select_main_document(documents)
        used_paths: list[str] = []
        used_path_set: set[str] = set()
        expansion_cache: dict[str, str] = {}

        def expand(path: str) -> str:
            if path in expansion_cache:
                return expansion_cache[path]

            if path not in used_path_set:
                used_path_set.add(path)
                used_paths.append(path)

            raw_text = self._strip_tex_comments(documents[path])
            pattern = re.compile(r"\\(?:input|include)\{([^}]+)\}")
            cursor = 0
            expanded_parts: list[str] = []
            for match in pattern.finditer(raw_text):
                expanded_parts.append(raw_text[cursor:match.start()])
                resolved_path = self._resolve_included_document(
                    match.group(1),
                    base_path=path,
                    documents=documents,
                )
                if resolved_path is not None and resolved_path != path:
                    expanded_parts.append(expand(resolved_path))
                cursor = match.end()

            expanded_parts.append(raw_text[cursor:])
            expanded_text = "".join(expanded_parts)
            expansion_cache[path] = expanded_text
            return expanded_text

        return expand(main_document), used_paths, main_document

    def _select_main_document(self, documents: dict[str, str]) -> str:
        best_path: str | None = None
        best_score = -1
        for path, text in documents.items():
            filename = PurePosixPath(path).name.lower()
            score = len(text)
            if "\\begin{document}" in text:
                score += 100_000
            if "\\documentclass" in text:
                score += 50_000
            if "\\title{" in text:
                score += 5_000
            if any(token in filename for token in ("main", "paper", "manuscript", "article", "ms")):
                score += 1_000
            if any(token in filename for token in ("appendix", "supp", "supplement")):
                score -= 5_000
            if score > best_score:
                best_score = score
                best_path = path

        if best_path is None:
            raise RuntimeError("could not identify a main TeX document in the source archive")
        return best_path

    def _resolve_included_document(
        self,
        reference: str,
        *,
        base_path: str,
        documents: dict[str, str],
    ) -> str | None:
        normalized_reference = reference.strip().strip('"')
        if not normalized_reference or normalized_reference.startswith("http"):
            return None

        base_dir = PurePosixPath(base_path).parent
        candidate_paths: list[str] = []
        reference_path = PurePosixPath(normalized_reference)

        if reference_path.suffix:
            candidate_paths.append((base_dir / reference_path).as_posix())
        else:
            candidate_paths.append((base_dir / reference_path).as_posix())
            candidate_paths.append((base_dir / f"{normalized_reference}.tex").as_posix())
            candidate_paths.append((base_dir / f"{normalized_reference}.ltx").as_posix())

        for candidate in candidate_paths:
            if candidate in documents:
                return candidate

        target_stem = PurePosixPath(normalized_reference).stem.lower()
        for document_path in documents:
            document_name = PurePosixPath(document_path)
            if document_name.stem.lower() == target_stem:
                return document_path

        return None

    def _extract_artifacts(
        self,
        documents: dict[str, str],
        *,
        used_paths: list[str],
    ) -> tuple[list[DocumentArtifact], list[DocumentArtifact]]:
        figure_items: list[DocumentArtifact] = []
        table_items: list[DocumentArtifact] = []
        used_path_set = set(used_paths)
        for path, text in documents.items():
            if used_path_set and path not in used_path_set:
                continue
            stripped_text = self._strip_tex_comments(text)
            figure_items.extend(self._extract_artifact_kind(stripped_text, path=path, kind="figure"))
            table_items.extend(self._extract_artifact_kind(stripped_text, path=path, kind="table"))
        return figure_items, table_items

    def _extract_artifact_kind(
        self,
        text: str,
        *,
        path: str,
        kind: str,
    ) -> list[DocumentArtifact]:
        pattern = re.compile(
            rf"\\begin\{{{kind}\*?\}}(.*?)\\end\{{{kind}\*?\}}",
            flags=re.DOTALL,
        )
        artifacts: list[DocumentArtifact] = []
        for match in pattern.finditer(text):
            body = match.group(1)
            caption = self._extract_command_argument(body, "caption")
            label = self._extract_command_argument(body, "label")
            referenced_files = re.findall(
                r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}",
                body,
            )
            referenced_files.extend(re.findall(r"\\(?:input|include)\{([^}]+)\}", body))
            artifacts.append(
                DocumentArtifact(
                    kind="figure" if kind == "figure" else "table",
                    label=label.strip() if label else None,
                    caption=self._clean_latex_fragment(caption) if caption else None,
                    source_path=path,
                    referenced_files=sorted({item.strip() for item in referenced_files if item.strip()}),
                )
            )
        return artifacts

    def _latex_to_text(self, latex_source: str) -> str:
        text = self._strip_tex_comments(latex_source)
        if "\\begin{document}" in text:
            text = text.split("\\begin{document}", 1)[1]
        if "\\end{document}" in text:
            text = text.split("\\end{document}", 1)[0]
        text = self._replace_artifact_environments(text, kind="figure")
        text = self._replace_artifact_environments(text, kind="table")

        for environment in (
            "equation",
            "equation*",
            "align",
            "align*",
            "gather",
            "gather*",
            "multline",
            "multline*",
            "displaymath",
            "tikzpicture",
            "thebibliography",
        ):
            text = re.sub(
                rf"\\begin\{{{re.escape(environment)}\}}.*?\\end\{{{re.escape(environment)}\}}",
                "\n\n",
                text,
                flags=re.DOTALL,
            )

        text = text.replace("\\begin{abstract}", "\n\nAbstract\n\n")
        text = text.replace("\\end{abstract}", "\n\n")

        for command in ("chapter", "section", "subsection", "subsubsection", "paragraph", "subparagraph", "title"):
            text = re.sub(
                rf"\\{command}\*?(?:\[[^\]]*\])?\{{([^{{}}]*)\}}",
                lambda match: f"\n\n{match.group(1).strip()}\n\n",
                text,
            )

        text = re.sub(r"\\author(?:\[[^\]]*\])?\{([^{}]*)\}", r"\n\n\1\n\n", text)
        text = re.sub(r"\\(cite|citet|citep|citealt|citeauthor|citeyear|ref|eqref|autoref|pageref)\*?(?:\[[^\]]*\])?\{([^{}]*)\}", r" [\1: \2] ", text)
        text = re.sub(r"\\label\{[^{}]*\}", " ", text)
        text = re.sub(r"\\href\{([^{}]*)\}\{([^{}]*)\}", r"\2 (\1)", text)
        text = re.sub(r"\\url\{([^{}]*)\}", r"\1", text)
        text = re.sub(r"\\footnote\{([^{}]*)\}", r" (\1) ", text)

        for _ in range(3):
            updated_text = re.sub(
                r"\\(?:emph|textbf|textit|textrm|textsf|texttt|underline|mbox|mathrm|mathbf|mathit|operatorname)\*?(?:\[[^\]]*\])?\{([^{}]*)\}",
                r"\1",
                text,
            )
            updated_text = re.sub(
                r"\\[a-zA-Z@]+\*?(?:\[[^\]]*\])?\{([^{}]*)\}",
                r"\1",
                updated_text,
            )
            if updated_text == text:
                break
            text = updated_text

        text = re.sub(r"\\begin\{[^}]+\}", "\n", text)
        text = re.sub(r"\\end\{[^}]+\}", "\n", text)
        text = re.sub(r"\\item", "\n- ", text)
        text = re.sub(r"\\\[(.*?)\\\]", " ", text, flags=re.DOTALL)
        text = re.sub(r"\\\((.*?)\\\)", " ", text, flags=re.DOTALL)
        text = re.sub(r"\$\$(.*?)\$\$", " ", text, flags=re.DOTALL)
        text = re.sub(r"\$(.*?)\$", " ", text, flags=re.DOTALL)
        text = text.replace("\\\\", "\n")
        text = text.replace("~", " ")
        text = re.sub(r"\\[a-zA-Z@]+\*?", " ", text)
        text = re.sub(r"\\.", " ", text)
        text = text.replace("{", " ").replace("}", " ")
        text = re.sub(r"[ \t\f\v]+", " ", text)
        text = re.sub(r"\n[ \t]+", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _replace_artifact_environments(self, text: str, *, kind: str) -> str:
        pattern = re.compile(
            rf"\\begin\{{{kind}\*?\}}(.*?)\\end\{{{kind}\*?\}}",
            flags=re.DOTALL,
        )

        def replace(match: re.Match[str]) -> str:
            caption = self._extract_command_argument(match.group(1), "caption")
            if not caption:
                return "\n\n"
            return f"\n\n{kind.title()}: {self._clean_latex_fragment(caption)}\n\n"

        return pattern.sub(replace, text)

    def _clean_latex_fragment(self, fragment: str) -> str:
        cleaned = self._latex_to_text(fragment)
        return cleaned.strip()

    @staticmethod
    def _strip_tex_comments(text: str) -> str:
        return re.sub(r"(?<!\\)%.*", "", text)

    def _extract_command_argument(self, text: str, command: str) -> str | None:
        pattern = re.compile(rf"\\{command}\*?")
        search_index = 0
        while True:
            match = pattern.search(text, search_index)
            if match is None:
                return None

            cursor = match.end()
            while cursor < len(text) and text[cursor].isspace():
                cursor += 1

            if cursor < len(text) and text[cursor] == "[":
                optional_end = self._find_matching_delimiter(text, cursor, "[", "]")
                if optional_end is None:
                    search_index = match.end()
                    continue
                cursor = optional_end + 1
                while cursor < len(text) and text[cursor].isspace():
                    cursor += 1

            if cursor < len(text) and text[cursor] == "{":
                argument_end = self._find_matching_delimiter(text, cursor, "{", "}")
                if argument_end is None:
                    search_index = match.end()
                    continue
                return text[cursor + 1:argument_end]

            search_index = match.end()

    @staticmethod
    def _find_matching_delimiter(text: str, start_index: int, opening: str, closing: str) -> int | None:
        depth = 0
        cursor = start_index
        while cursor < len(text):
            character = text[cursor]
            if character == "\\":
                cursor += 2
                continue
            if character == opening:
                depth += 1
            elif character == closing:
                depth -= 1
                if depth == 0:
                    return cursor
            cursor += 1
        return None

    @staticmethod
    def _truncate_text(text: str, max_characters: int | None) -> tuple[str, bool]:
        if max_characters is None or len(text) <= max_characters:
            return text, False
        return text[:max_characters].rstrip(), True

    @staticmethod
    def _normalize_extraction_preference(prefer: str) -> str:
        normalized_preference = prefer.strip().lower()
        if normalized_preference not in {"source", "pdf"}:
            raise ValueError("prefer must be either 'source' or 'pdf'.")
        return normalized_preference

    @staticmethod
    def _normalize_max_characters(max_characters: int | None) -> int | None:
        if max_characters is None or max_characters <= 0:
            return None
        if max_characters > 2_000_000:
            raise ValueError("max_characters must be 0 or a value between 1 and 2000000.")
        return max_characters

    @staticmethod
    def _detect_payload_kind(payload: bytes, *, content_type: str | None = None) -> str:
        normalized_content_type = (content_type or "").lower()
        if "pdf" in normalized_content_type or payload.startswith(b"%PDF-"):
            return "pdf"
        if payload.startswith(b"\x1f\x8b"):
            return "gzip"
        if payload.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
            return "zip"
        if len(payload) > 262 and payload[257:262] == b"ustar":
            return "tar"
        try:
            sample = payload[:4096].decode("utf-8")
        except UnicodeDecodeError:
            try:
                sample = payload[:4096].decode("latin-1")
            except UnicodeDecodeError:
                return "unknown"

        if any(token in sample for token in ("\\documentclass", "\\begin{document}", "\\section", "\\title{")):
            return "text"
        return "unknown"

    @staticmethod
    def _normalize_identifier(arxiv_id: str) -> str:
        normalized_identifier = arxiv_id.strip()
        if not normalized_identifier:
            raise ValueError("arxiv_id must not be empty.")

        lowered = normalized_identifier.lower()
        if lowered.startswith("arxiv:"):
            return normalized_identifier.split(":", 1)[1]
        if "/abs/" in lowered:
            return normalized_identifier.rsplit("/", 1)[-1]
        if "/pdf/" in lowered:
            return normalized_identifier.rsplit("/", 1)[-1].removesuffix(".pdf")

        return normalized_identifier