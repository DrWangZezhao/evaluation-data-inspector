"""Streamlit UI for the APA 7–aligned Evaluation Data Inspector."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from analysis import AnalysisError
from inspector.exports import export_docx, export_html
from inspector.i18n import LANGUAGE_OPTIONS, t
from inspector.ingest import ENCODINGS, SEPARATORS, ParsedData, infer_roles, inspect_xlsx, parse_upload
from inspector.llm import DEFAULT_MODEL
from inspector.models import Language, VariableRole
from inspector.pipeline import ReportSettings, generate_report


APP_DIR = Path(__file__).resolve().parent
SAMPLE_PATH = APP_DIR / "sample_data" / "sample_evaluation_data.csv"
ROLE_OPTIONS: list[VariableRole] = ["identifier", "numeric", "categorical", "ordinal", "date", "text"]
UI_TEXT: dict[Language, dict[str, str]] = {
    "en": {"variables": "Variables to include", "sections": "Optional report sections", "roles": "Variable roles and labels", "display_label": "Display label for {label}", "unit": "Optional unit for {label}", "valid_range": "Optional valid range for {label} (min,max)", "invalid_range": "Use two decimal-point numbers separated by a comma; either bound may be blank.", "role_help": "Inferred role; override only when study knowledge supports it.", "chart": "Chart recommendation", "recommended": "Recommended", "histogram": "Histogram first", "bar": "Category bar first", "missingness": "Missingness first", "diagnostics": "Raw preview and parsing diagnostics", "payload": "AI payload preview", "payload_facts": "Up to 30 selected aggregate facts", "select_variable": "Select at least one variable.", "settings_changed": "Settings changed. Generate the report again to refresh the preview and downloads.", "generating": "Generating report…", "note": "Note.", "model_note": "Model: {model}. One request, with at most one validation retry; raw data are never included."},
    "zh-CN": {"variables": "要纳入的变量", "sections": "可选报告章节", "roles": "变量角色与标签", "display_label": "{label} 的显示标签", "unit": "{label} 的可选单位", "valid_range": "{label} 的可选有效范围（最小值,最大值）", "invalid_range": "请用逗号分隔两个小数点格式的数值；任一边界可留空。", "role_help": "这是推断角色；仅在研究知识支持时覆盖。", "chart": "图形建议", "recommended": "推荐", "histogram": "直方图优先", "bar": "分类条形图优先", "missingness": "缺失率图优先", "diagnostics": "原始数据预览与解析诊断", "payload": "AI 发送内容预览", "payload_facts": "最多 30 条经筛选的汇总事实", "select_variable": "请至少选择一个变量。", "settings_changed": "设置已更改。请重新生成报告以刷新预览和下载文件。", "generating": "正在生成报告…", "note": "注：", "model_note": "模型：{model}。发起一次请求，验证失败时最多重试一次；绝不包含原始数据。"},
    "es": {"variables": "Variables que se incluirán", "sections": "Secciones opcionales del informe", "roles": "Roles y etiquetas de variables", "display_label": "Etiqueta visible de {label}", "unit": "Unidad opcional de {label}", "valid_range": "Rango válido opcional de {label} (mín,máx)", "invalid_range": "Use dos números con punto decimal separados por coma; cualquier límite puede quedar vacío.", "role_help": "Rol inferido; modifíquelo solo si lo respalda el conocimiento del estudio.", "chart": "Recomendación de gráfico", "recommended": "Recomendado", "histogram": "Histograma primero", "bar": "Barras de categorías primero", "missingness": "Ausencia primero", "diagnostics": "Vista de datos y diagnóstico del archivo", "payload": "Vista previa de datos para la IA", "payload_facts": "Hasta 30 resultados agregados seleccionados", "select_variable": "Seleccione al menos una variable.", "settings_changed": "La configuración cambió. Genere de nuevo el informe para actualizar la vista y las descargas.", "generating": "Generando informe…", "note": "Nota.", "model_note": "Modelo: {model}. Una solicitud y, como máximo, un reintento de validación; nunca se incluyen datos sin procesar."},
    "fi": {"variables": "Raporttiin sisällytettävät muuttujat", "sections": "Valinnaiset raporttiosiot", "roles": "Muuttujien roolit ja nimet", "display_label": "Muuttujan {label} näyttönimi", "unit": "Muuttujan {label} valinnainen yksikkö", "valid_range": "Muuttujan {label} valinnainen kelvollinen väli (min,max)", "invalid_range": "Anna kaksi desimaalipistettä käyttävää lukua pilkulla erotettuina; kumman tahansa rajan voi jättää tyhjäksi.", "role_help": "Päätelty rooli; muuta vain tutkimustiedon perusteella.", "chart": "Kuviosuositus", "recommended": "Suositeltu", "histogram": "Histogrammi ensin", "bar": "Luokkapylväät ensin", "missingness": "Puuttuvat tiedot ensin", "diagnostics": "Raakatietojen esikatselu ja jäsennysdiagnostiikka", "payload": "Tekoälylle lähetettävien tietojen esikatselu", "payload_facts": "Enintään 30 valittua koontitietoa", "select_variable": "Valitse vähintään yksi muuttuja.", "settings_changed": "Asetukset muuttuivat. Luo raportti uudelleen päivittääksesi esikatselun ja lataukset.", "generating": "Raporttia luodaan…", "note": "Huom.", "model_note": "Malli: {model}. Yksi pyyntö ja enintään yksi validoinnin uudelleenyritys; raakatietoja ei koskaan sisällytetä."},
}


def _ui(language: Language, key: str, **kwargs: object) -> str:
    value = UI_TEXT[language][key]
    return value.format(**kwargs) if kwargs else value


def _init_state() -> None:
    defaults = {
        "state": "EMPTY", "uploaded_bytes": None, "uploaded_name": "", "parsed": None,
        "report": None, "analysis": None, "docx": None, "html": None,
        "report_fingerprint": None, "uploader_key": 0, "ai_attempts": 0,
        "report_language": "English",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def _clear() -> None:
    for key in ("uploaded_bytes", "uploaded_name", "parsed", "report", "analysis", "docx", "html", "report_fingerprint"):
        st.session_state[key] = None if key != "uploaded_name" else ""
    st.session_state.state = "EMPTY"
    st.session_state.ai_attempts = 0
    st.session_state.uploader_key += 1


def _secret(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value is not None:
        return value
    try:
        return str(st.secrets.get(name, default))
    except Exception:
        return default


def _fingerprint(content: bytes, sheet: str | None, settings: ReportSettings, parsing: dict[str, str], included: list[str]) -> str:
    digest = hashlib.sha256()
    digest.update(content)
    payload = {"sheet": sheet, "parsing": parsing, "included": included, "settings": settings.model_dump(mode="json"), "schema": "1.0", "prompt": "1.0"}
    digest.update(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8"))
    return digest.hexdigest()


def _option_maps(language: Language) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    report_types = {
        "en": {"Automatic": "automatic", "Descriptive": "descriptive", "Data quality": "data_quality", "Group comparison": "group", "Relationships": "relationships", "Change over time": "change", "Date series": "time"},
        "zh-CN": {"自动": "automatic", "描述性报告": "descriptive", "数据质量": "data_quality", "组间比较": "group", "变量关系": "relationships", "前后变化": "change", "日期序列": "time"},
        "es": {"Automático": "automatic", "Descriptivo": "descriptive", "Calidad de datos": "data_quality", "Comparación de grupos": "group", "Relaciones": "relationships", "Cambio temporal": "change", "Serie por fecha": "time"},
        "fi": {"Automaattinen": "automatic", "Kuvaileva": "descriptive", "Aineiston laatu": "data_quality", "Ryhmävertailu": "group", "Yhteydet": "relationships", "Muutos": "change", "Aikasarja": "time"},
    }[language]
    audiences = {
        "en": {"Researcher": "researcher", "Educator": "educator", "Business/management": "business", "General audience": "general"},
        "zh-CN": {"研究人员": "researcher", "教育工作者": "educator", "商业/管理": "business", "一般读者": "general"},
        "es": {"Investigación": "researcher", "Educación": "educator", "Empresa/gestión": "business", "Público general": "general"},
        "fi": {"Tutkija": "researcher", "Kouluttaja": "educator", "Liiketoiminta/johto": "business", "Yleinen yleisö": "general"},
    }[language]
    depths = {
        "en": {"Brief": "brief", "Standard": "standard", "Detailed": "detailed"},
        "zh-CN": {"简要": "brief", "标准": "standard", "详细": "detailed"},
        "es": {"Breve": "brief", "Estándar": "standard", "Detallado": "detailed"},
        "fi": {"Lyhyt": "brief", "Tavallinen": "standard", "Laaja": "detailed"},
    }[language]
    return report_types, audiences, depths


def _render_report(report) -> None:
    st.divider()
    st.caption(report.status_note)
    st.header(report.title)
    st.caption(report.subtitle)
    table_number = 0
    figure_number = 0
    for section in report.sections:
        st.subheader(section.heading)
        for paragraph in section.paragraphs:
            st.write(paragraph)
        for table in section.tables:
            table_number += 1
            st.markdown(f"**{t(report.language, 'table')} {table_number}**  \n*{table.title}*")
            st.dataframe(pd.DataFrame(table.rows, columns=table.columns), hide_index=True, width="stretch")
            if table.note:
                st.caption(f"{_ui(report.language, 'note')} {table.note}")
        for figure in section.figures:
            figure_number += 1
            st.markdown(f"**{t(report.language, 'figure')} {figure_number}**  \n*{figure.title}*")
            st.image(figure.png, caption=figure.caption, width="stretch")


def main() -> None:
    st.set_page_config(page_title="Evaluation Data Inspector", page_icon="📄", layout="centered")
    _init_state()
    language: Language = LANGUAGE_OPTIONS[st.session_state.report_language]  # type: ignore[assignment]
    st.title("Evaluation Data Inspector")
    st.markdown(f"### {t(language, 'subtitle')}")

    upload = st.file_uploader(t(language, "upload"), type=("csv", "xlsx"), key=f"upload_{st.session_state.uploader_key}")
    st.selectbox("Report language / 报告语言 / Idioma / Kieli", list(LANGUAGE_OPTIONS), key="report_language")
    if upload is not None:
        new_bytes = upload.getvalue()
        if new_bytes != st.session_state.uploaded_bytes or upload.name != st.session_state.uploaded_name:
            st.session_state.uploaded_bytes = new_bytes
            st.session_state.uploaded_name = upload.name
            st.session_state.report = None
            st.session_state.report_fingerprint = None
    content: bytes | None = st.session_state.uploaded_bytes
    filename = st.session_state.uploaded_name

    parsing_defaults = st.session_state.setdefault("parsing_options", {"encoding": "UTF-8", "separator": "Automatic", "decimal": "."})
    selected_sheet: str | None = None
    parsed: ParsedData | None = None
    if content:
        try:
            if filename.lower().endswith(".xlsx"):
                sheet_names = inspect_xlsx(content)
                selected_sheet = st.selectbox(t(language, "sheet"), sheet_names) if len(sheet_names) > 1 else sheet_names[0]
            parsed = parse_upload(content, filename, sheet_name=selected_sheet, encoding=ENCODINGS[parsing_defaults["encoding"]], separator=SEPARATORS[parsing_defaults["separator"]], decimal=parsing_defaults["decimal"])
            st.session_state.state = "READY"
            st.success(t(language, "ready", rows=len(parsed.data), columns=len(parsed.data.columns)))
        except AnalysisError as exc:
            st.session_state.state = "INVALID_INPUT"
            st.error(t(language, "invalid", message=str(exc)))

    generate_clicked = st.button(t(language, "generate"), type="primary", disabled=parsed is None, width="stretch")
    report_types, audiences, depths = _option_maps(language)
    role_overrides: dict[str, VariableRole] = {}
    label_overrides: dict[str, str] = {}
    units: dict[str, str] = {}
    valid_ranges: dict[str, tuple[float | None, float | None]] = {}
    range_error = False
    included: list[str] = list(parsed.data.columns) if parsed else []
    sections = ["overview", "quality", "descriptive", "figures", "interpretation"]
    report_type = "automatic"
    audience = "researcher"
    depth = "standard"
    study_title = study_context = ""
    manual_chart = None
    outcome = group = first = second = pre = post = date_variable = time_outcome = None
    independent = paired = False
    ai_enabled = share_labels = False
    api_key = _secret("GEMINI_API_KEY")
    model = _secret("GEMINI_MODEL", DEFAULT_MODEL) or DEFAULT_MODEL
    paid_service = _secret("GEMINI_PAID_SERVICE", "false").strip().lower() == "true"

    with st.expander(t(language, "advanced"), expanded=False):
        if filename.lower().endswith(".csv") if filename else False:
            encoding_label = st.selectbox(t(language, "encoding"), list(ENCODINGS), index=list(ENCODINGS).index(parsing_defaults["encoding"]))
            separator_label = st.selectbox(t(language, "separator"), list(SEPARATORS), index=list(SEPARATORS).index(parsing_defaults["separator"]))
            decimal = st.selectbox(t(language, "decimal"), [".", ","], index=0 if parsing_defaults["decimal"] == "." else 1)
            changed = {"encoding": encoding_label, "separator": separator_label, "decimal": decimal}
            if changed != parsing_defaults:
                st.session_state.parsing_options = changed
                st.session_state.report = None
                st.session_state.report_fingerprint = None
                st.rerun()
        report_label = st.selectbox(t(language, "report_type"), list(report_types))
        report_type = report_types[report_label]
        audience_label = st.selectbox(t(language, "audience"), list(audiences), index=0)
        audience = audiences[audience_label]
        depth_label = st.selectbox(t(language, "depth"), list(depths), index=1)
        depth = depths[depth_label]
        study_title = st.text_input(t(language, "study_title"), max_chars=200)
        study_context = st.text_area(t(language, "context"), max_chars=2000, height=90)
        section_options = {
            t(language, "overview"): "overview", t(language, "quality"): "quality",
            t(language, "descriptive"): "descriptive", t(language, "figures"): "figures",
            t(language, "interpretation"): "interpretation",
        }
        selected_section_labels = st.multiselect(_ui(language, "sections"), list(section_options), default=list(section_options))
        sections = [section_options[label] for label in selected_section_labels]
        if parsed:
            included = st.multiselect(_ui(language, "variables"), list(parsed.data.columns), default=list(parsed.data.columns))
            inferred = infer_roles(parsed.data, parsed.column_ids)
            with st.expander(_ui(language, "roles"), expanded=False):
                for column in inferred:
                    selected_role = st.selectbox(column.label, ROLE_OPTIONS, index=ROLE_OPTIONS.index(column.role), key=f"role_{column.id}", help=_ui(language, "role_help"))
                    if selected_role != column.role:
                        role_overrides[column.label] = selected_role
                    display_label = st.text_input(_ui(language, "display_label", label=column.label), value=column.label, max_chars=120, key=f"label_{column.id}")
                    if display_label.strip() and display_label.strip() != column.label:
                        label_overrides[column.label] = display_label.strip()
                    if selected_role == "numeric":
                        unit = st.text_input(_ui(language, "unit", label=column.label), max_chars=40, key=f"unit_{column.id}")
                        if unit.strip():
                            units[column.label] = unit.strip()
                        range_text = st.text_input(_ui(language, "valid_range", label=column.label), max_chars=80, key=f"range_{column.id}")
                        if range_text.strip():
                            try:
                                parts = range_text.split(",")
                                if len(parts) != 2:
                                    raise ValueError
                                minimum = float(parts[0].strip()) if parts[0].strip() else None
                                maximum = float(parts[1].strip()) if parts[1].strip() else None
                                if minimum is None and maximum is None:
                                    raise ValueError
                                valid_ranges[column.label] = (minimum, maximum)
                            except ValueError:
                                range_error = True
                                st.warning(_ui(language, "invalid_range"))
            effective = infer_roles(parsed.data, parsed.column_ids, role_overrides)
            numeric = [column.label for column in effective if column.role == "numeric" and column.label in included]
            groups = [column.label for column in effective if column.role in {"categorical", "ordinal"} and 2 <= column.unique_nonmissing <= 20 and column.label in included]
            dates = [column.label for column in effective if column.role == "date" and column.label in included]
            if report_type == "group":
                outcome = st.selectbox(t(language, "outcome"), numeric) if numeric else None
                group = st.selectbox(t(language, "group"), groups) if groups else None
                independent = st.checkbox(t(language, "independent"))
            elif report_type == "relationships":
                first = st.selectbox(t(language, "x_variable"), numeric) if numeric else None
                remaining = [item for item in numeric if item != first]
                second = st.selectbox(t(language, "y_variable"), remaining) if remaining else None
            elif report_type == "change":
                pre = st.selectbox(t(language, "pre"), numeric) if numeric else None
                remaining = [item for item in numeric if item != pre]
                post = st.selectbox(t(language, "post"), remaining) if remaining else None
                paired = st.checkbox(t(language, "paired"))
            elif report_type == "time":
                date_variable = st.selectbox(t(language, "date"), dates) if dates else None
                time_outcome = st.selectbox(t(language, "outcome"), numeric) if numeric else None
            chart_options = {_ui(language, "recommended"): None, _ui(language, "histogram"): "histogram", _ui(language, "bar"): "bar", _ui(language, "missingness"): "missingness"}
            chart_label = st.selectbox(_ui(language, "chart"), list(chart_options))
            manual_chart = chart_options[chart_label]
            with st.expander(_ui(language, "diagnostics"), expanded=False):
                st.dataframe(parsed.data.head(20), hide_index=True, width="stretch")
                for note in parsed.notes:
                    st.caption(note)
        ai_available = bool(api_key and paid_service)
        ai_enabled = st.checkbox(t(language, "ai"), disabled=not ai_available)
        if not ai_available:
            st.caption(t(language, "ai_unavailable"))
        st.caption(t(language, "ai_disclosure"))
        share_labels = st.checkbox(t(language, "labels"), disabled=not ai_enabled)
        with st.expander(_ui(language, "payload"), expanded=False):
            st.json({"language": language, "audience": audience, "depth": depth, "facts": _ui(language, "payload_facts"), "study_context_shared": bool(ai_enabled and study_context.strip()), "reviewed_labels_shared": bool(ai_enabled and share_labels), "raw_rows_or_text_cells": False})
        if ai_enabled:
            st.caption(_ui(language, "model_note", model=model))

    secondary, clear_column = st.columns(2)
    if secondary.button(t(language, "try_sample"), type="secondary", width="stretch"):
        st.session_state.uploaded_bytes = SAMPLE_PATH.read_bytes()
        st.session_state.uploaded_name = SAMPLE_PATH.name
        st.session_state.report = None
        st.session_state.report_fingerprint = None
        st.rerun()
    if clear_column.button(t(language, "clear"), width="stretch"):
        _clear()
        st.rerun()
    st.caption(t(language, "privacy"))

    if parsed and content:
        if not included:
            st.warning(_ui(language, "select_variable"))
        settings = ReportSettings(language=language, report_type=report_type, audience=audience, depth=depth, study_title=study_title, study_context=study_context, sections=sections, role_overrides=role_overrides, label_overrides=label_overrides, units=units, valid_ranges=valid_ranges, outcome=outcome, group=group, independent_groups=independent, relationship_first=first, relationship_second=second, pre=pre, post=post, paired_confirmed=paired, date_variable=date_variable, time_outcome=time_outcome, manual_chart_kind=manual_chart, ai_enabled=ai_enabled, share_labels=share_labels, model=model)
        current_fingerprint = _fingerprint(content, selected_sheet, settings, st.session_state.parsing_options, included)
        if st.session_state.report_fingerprint and st.session_state.report_fingerprint != current_fingerprint:
            st.info(_ui(language, "settings_changed"))
        if generate_clicked and included and not range_error:
            if st.session_state.report_fingerprint != current_fingerprint:
                st.session_state.state = "GENERATING"
                selected_parsed = ParsedData(data=parsed.data[included].copy(), sheet_names=parsed.sheet_names, selected_sheet=parsed.selected_sheet, notes=parsed.notes, column_ids={label: parsed.column_ids[label] for label in included})
                try:
                    with st.spinner(_ui(language, "generating")):
                        output = generate_report(selected_parsed, settings, gemini_api_key=api_key, gemini_paid_service=paid_service, session_ai_attempts=st.session_state.ai_attempts)
                        st.session_state.report = output.report
                        st.session_state.analysis = output.analysis
                        st.session_state.docx = export_docx(output.report)
                        st.session_state.html = export_html(output.report)
                        st.session_state.report_fingerprint = current_fingerprint
                        st.session_state.ai_attempts += output.ai_attempts
                        st.session_state.state = "COMPLETE"
                except AnalysisError as exc:
                    st.session_state.state = "INVALID_INPUT"
                    st.error(str(exc))
        if st.session_state.report is not None and st.session_state.report_fingerprint == current_fingerprint:
            _render_report(st.session_state.report)
            first_download, second_download = st.columns(2)
            first_download.download_button(t(language, "download_docx"), st.session_state.docx, "evaluation-report.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", width="stretch")
            second_download.download_button(t(language, "download_html"), st.session_state.html, "evaluation-report.html", "text/html", width="stretch")
            st.caption(t(language, "print_note"))


if __name__ == "__main__":
    main()
