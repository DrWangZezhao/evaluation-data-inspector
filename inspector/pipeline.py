"""Pure parse-independent orchestration for deterministic report generation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

import pandas as pd
from pydantic import Field

from analysis import (
    AnalysisError, categorical_summary, cohens_d, date_mean_series,
    group_statistics_detailed, numeric_summary, paired_change_statistics,
    pearson_relationship,
)
from . import APP_VERSION, PROMPT_VERSION, SCHEMA_VERSION
from .charts import render_chart, select_charts
from .i18n import format_number, t
from .ingest import ParsedData, infer_roles
from .llm import DEFAULT_MODEL, GeminiConfig
from .models import (
    AnalysisResult, ChartSpec, EvidenceFact, FigureBlock, Language, ReportDocument,
    ReportSection, ReportType, StrictModel, TableBlock, VariableRole,
)
from .narrative import build_ai_payload, expand_fact_tokens, request_validated_narrative


REPORT_TEXT: dict[Language, dict[str, str]] = {
    "en": {
        "roles_review": "Variable roles were inferred conservatively and should be reviewed.",
        "quality_summary": "{duplicates} duplicate rows were flagged; none were removed. Constants: {constants}. Possible identifier duplicates: {id_duplicates}.",
        "none": "none", "finite_note": "Finite valid observations; sample SD uses ddof=1.",
        "category_title": "Frequencies for {label}", "category_note": "Percentages use all {n} valid observations as the denominator.",
        "category_intro": "Categorical frequencies use valid (non-missing) observations as the denominator.", "outside_range": "Outside supplied range", "range_finding": "{label}: {count} finite values fall outside the user-supplied range {minimum} to {maximum}; values were flagged, not removed.",
        "effect_unavailable": "Cohen's d requires two explicitly confirmed independent groups.",
        "effect": "Using first-observed order ({direction}), the mean difference was {difference} and pooled-SD Cohen's d was {effect}.",
        "relationship": "Pearson r for {first} and {second} used {n} pairwise-complete finite observations and was {r}; it describes linear association only.",
        "relationship_unavailable": "Pearson r was unavailable ({reason}); pairwise n = {n}.",
        "change": "On the identical {n} complete pairs, post minus pre change had M = {mean}, SD = {sd}, and median = {median}; direction was not interpreted as improvement.",
        "time": "The date-level series used {n} finite observations; duplicate dates were aggregated by mean and no interpolation was applied.",
        "figure_intro": "Figure {number} presents {title}.", "valid_caption": "{title}. Valid n = {n}. {notes}",
        "alt": "{kind} chart: {title}; valid n {n}",
        "interpretation_text": "Observed patterns should be interpreted in light of the study design and measurement context supplied by the user; the application does not verify that context.",
        "lim_roles": "Variable roles are inferred and may require correction.",
        "lim_missing": "Missing values were excluded analysis by analysis; no missingness mechanism was inferred.",
        "lim_public": "This public demonstration is not an approved environment for confidential, clinical, or regulated data.",
        "generated": "Generated UTC: {timestamp}.",
        "repro_missing": "Original missingness is reported separately from non-finite numeric exclusions.",
        "repro_charts": "Charts use complete eligible data; scatter display sampling is fixed-seed and capped at 5,000 points.",
        "repro_settings": "Report type: {report_type}; audience: {audience}; depth: {depth}.",
        "parsing": "Parsing: {notes}", "xlsx_parse": "Worksheet: {sheet}. Trailing empty padding was ignored; internal blank records were preserved.", "formula_parse": "Formula cells use cached workbook results, which may be stale or absent; formulas were not evaluated.", "link_parse": "External workbook links were not loaded.", "csv_parse": "CSV encoding: {encoding}; separator: {separator}; decimal mark: {decimal}.", "omitted": "Chart budget omitted: {labels}.",
        "group_note": "All observed groups are retained.",
        "scatter_note": "At most 5,000 display points, fixed seed; analysis uses all eligible pairs.",
        "change_note": "Change is post minus pre; score direction is not interpreted as improvement.",
        "time_note": "Duplicate dates are aggregated by mean with observation counts; no interpolation.",
        "category_limit": "Frequency tables were limited to the first 20 eligible categorical variables; complete summaries remain in the validated analysis object.",
    },
    "zh-CN": {
        "roles_review": "变量角色采用保守规则推断，建议结合研究知识复核。",
        "quality_summary": "共标记 {duplicates} 个重复行，未删除任何记录。常量变量：{constants}。可能存在重复值的标识变量：{id_duplicates}。",
        "none": "无", "finite_note": "仅使用有限有效观测；样本标准差采用 ddof=1。",
        "category_title": "{label} 的频数", "category_note": "百分比以全部 {n} 个有效观测为分母。",
        "category_intro": "分类变量百分比以有效（非缺失）观测为分母。", "outside_range": "超出指定范围", "range_finding": "{label}：有 {count} 个有限值超出用户指定范围 {minimum} 至 {maximum}；这些值仅被标记，未被删除。",
        "effect_unavailable": "仅在明确确认两个组相互独立时计算 Cohen's d。",
        "effect": "按首次出现顺序（{direction}），均值差为 {difference}，合并标准差 Cohen's d 为 {effect}。",
        "relationship": "{first} 与 {second} 的 Pearson r 使用 {n} 个成对完整的有限观测，结果为 {r}；该结果仅描述线性关联。",
        "relationship_unavailable": "无法计算 Pearson r（{reason}）；成对样本量 n = {n}。",
        "change": "在相同的 {n} 个完整配对中，后测减前测的变化为 M = {mean}、SD = {sd}、中位数 = {median}；未将变化方向解释为改善。",
        "time": "日期序列使用 {n} 个有限观测；同日记录按均值聚合，未进行插值。",
        "figure_intro": "图 {number} 展示{title}。", "valid_caption": "{title}。有效 n = {n}。{notes}",
        "alt": "{kind} 图：{title}；有效 n 为 {n}",
        "interpretation_text": "观察到的模式应结合用户提供的研究设计与测量背景解释；本应用不会核实这些背景信息。",
        "lim_roles": "变量角色由规则推断，可能需要人工修正。",
        "lim_missing": "各项分析分别排除缺失值；未推断缺失机制。",
        "lim_public": "此公共演示环境不适合处理机密、临床或受监管的数据。",
        "generated": "生成时间（UTC）：{timestamp}。",
        "repro_missing": "原始缺失值与数值变量中的非有限值排除分别报告。",
        "repro_charts": "图形使用全部符合条件的数据；散点图展示采用固定随机种子，最多 5,000 个点。",
        "repro_settings": "报告类型：{report_type}；受众：{audience}；详细程度：{depth}。",
        "parsing": "解析信息：{notes}", "xlsx_parse": "工作表：{sheet}。已忽略末尾空白填充，并保留数据内部的空白记录。", "formula_parse": "公式单元格使用工作簿缓存结果，该结果可能过期或缺失；未执行公式。", "link_parse": "未加载外部工作簿链接。", "csv_parse": "CSV 编码：{encoding}；分隔符：{separator}；小数符号：{decimal}。", "omitted": "因图形数量上限未展示：{labels}。",
        "group_note": "保留所有已观测分组。",
        "scatter_note": "最多展示 5,000 个点并采用固定随机种子；分析使用全部符合条件的配对。",
        "change_note": "变化定义为后测减前测；不将分数方向解释为改善。",
        "time_note": "同一日期按均值及观测数聚合；不进行插值。",
        "category_limit": "频数表仅展示前 20 个符合条件的分类变量；完整汇总仍保留在经验证的分析对象中。",
    },
    "es": {
        "roles_review": "Los roles se infirieron de forma conservadora y deben revisarse.",
        "quality_summary": "Se marcaron {duplicates} filas duplicadas; no se eliminó ninguna. Constantes: {constants}. Posibles duplicados en identificadores: {id_duplicates}.",
        "none": "ninguno", "finite_note": "Observaciones válidas finitas; la DE muestral usa ddof=1.",
        "category_title": "Frecuencias de {label}", "category_note": "Los porcentajes usan las {n} observaciones válidas como denominador.",
        "category_intro": "Las frecuencias categóricas usan las observaciones válidas (no faltantes) como denominador.", "outside_range": "Fuera del rango indicado", "range_finding": "{label}: {count} valores finitos están fuera del rango indicado por el usuario, de {minimum} a {maximum}; se marcaron, no se eliminaron.",
        "effect_unavailable": "La d de Cohen requiere dos grupos independientes confirmados explícitamente.",
        "effect": "Según el orden de primera aparición ({direction}), la diferencia de medias fue {difference} y la d de Cohen con DE combinada fue {effect}.",
        "relationship": "La r de Pearson entre {first} y {second} usó {n} pares completos finitos y fue {r}; solo describe asociación lineal.",
        "relationship_unavailable": "No se pudo calcular la r de Pearson ({reason}); n por pares = {n}.",
        "change": "En los mismos {n} pares completos, el cambio post menos pre tuvo M = {mean}, DE = {sd} y mediana = {median}; la dirección no se interpretó como mejora.",
        "time": "La serie por fecha usó {n} observaciones finitas; las fechas repetidas se agregaron mediante la media, sin interpolación.",
        "figure_intro": "La Figura {number} presenta {title}.", "valid_caption": "{title}. n válido = {n}. {notes}",
        "alt": "Gráfico {kind}: {title}; n válido {n}",
        "interpretation_text": "Los patrones observados deben interpretarse según el diseño del estudio y el contexto de medición aportado; la aplicación no verifica ese contexto.",
        "lim_roles": "Los roles de las variables se infieren y pueden requerir corrección.",
        "lim_missing": "Los valores faltantes se excluyeron en cada análisis; no se infirió su mecanismo.",
        "lim_public": "Esta demostración pública no está aprobada para datos confidenciales, clínicos o regulados.",
        "generated": "Generado en UTC: {timestamp}.",
        "repro_missing": "La ausencia original se informa por separado de las exclusiones numéricas no finitas.",
        "repro_charts": "Los gráficos usan todos los datos elegibles; la muestra visual del diagrama de dispersión tiene semilla fija y un máximo de 5.000 puntos.",
        "repro_settings": "Tipo de informe: {report_type}; audiencia: {audience}; extensión: {depth}.",
        "parsing": "Análisis del archivo: {notes}", "xlsx_parse": "Hoja: {sheet}. Se ignoró el relleno vacío final y se conservaron los registros vacíos internos.", "formula_parse": "Las fórmulas usan resultados almacenados en el libro, que pueden estar desactualizados o ausentes; no se evaluaron.", "link_parse": "No se cargaron enlaces a libros externos.", "csv_parse": "Codificación CSV: {encoding}; separador: {separator}; marca decimal: {decimal}.", "omitted": "El límite de gráficos omitió: {labels}.",
        "group_note": "Se conservan todos los grupos observados.",
        "scatter_note": "Se muestran como máximo 5.000 puntos con semilla fija; el análisis usa todos los pares elegibles.",
        "change_note": "El cambio es post menos pre; la dirección no se interpreta como mejora.",
        "time_note": "Las fechas repetidas se agregan por media y recuento; no se interpola.",
        "category_limit": "Las tablas de frecuencias se limitaron a las primeras 20 variables categóricas elegibles; los resúmenes completos permanecen en el objeto de análisis validado.",
    },
    "fi": {
        "roles_review": "Muuttujien roolit pääteltiin varovaisin säännöin, ja ne tulee tarkistaa.",
        "quality_summary": "Päällekkäisiä rivejä merkittiin {duplicates}; yhtään ei poistettu. Vakiomuuttujat: {constants}. Mahdolliset tunnistemuuttujien kaksoisarvot: {id_duplicates}.",
        "none": "ei yhtään", "finite_note": "Äärelliset kelvolliset havainnot; otoskeskihajonta käyttää arvoa ddof=1.",
        "category_title": "Muuttujan {label} frekvenssit", "category_note": "Prosenttien nimittäjänä ovat kaikki {n} kelvollista havaintoa.",
        "category_intro": "Luokkamuuttujien prosenttien nimittäjänä ovat kelvolliset (ei-puuttuvat) havainnot.", "outside_range": "Ilmoitetun vaihteluvälin ulkopuolella", "range_finding": "{label}: {count} äärellistä arvoa on käyttäjän ilmoittaman vaihteluvälin {minimum}–{maximum} ulkopuolella; arvot merkittiin, niitä ei poistettu.",
        "effect_unavailable": "Cohenin d edellyttää kahta nimenomaisesti riippumattomiksi vahvistettua ryhmää.",
        "effect": "Ensimmäisen esiintymisen järjestyksessä ({direction}) keskiarvojen ero oli {difference} ja yhdistettyyn keskihajontaan perustuva Cohenin d oli {effect}.",
        "relationship": "Muuttujien {first} ja {second} Pearsonin r perustui {n} parittaiseen äärelliseen havaintoon ja oli {r}; se kuvaa vain lineaarista yhteyttä.",
        "relationship_unavailable": "Pearsonin r ei ollut laskettavissa ({reason}); parittainen n = {n}.",
        "change": "Samoissa {n} täydellisessä havaintoparissa loppu- ja alkumittauksen erotuksen KA = {mean}, KH = {sd} ja mediaani = {median}; suuntaa ei tulkittu paranemiseksi.",
        "time": "Päivätason sarja käytti {n} äärellistä havaintoa; samojen päivien havainnot yhdistettiin keskiarvolla ilman interpolointia.",
        "figure_intro": "Kuvio {number} esittää: {title}.", "valid_caption": "{title}. Kelvollinen n = {n}. {notes}",
        "alt": "{kind}-kuvio: {title}; kelvollinen n {n}",
        "interpretation_text": "Havaittuja malleja tulee tulkita käyttäjän ilmoittaman tutkimusasetelman ja mittauskontekstin valossa; sovellus ei varmista niitä.",
        "lim_roles": "Muuttujien roolit on päätelty, ja ne voivat vaatia korjausta.",
        "lim_missing": "Puuttuvat arvot rajattiin pois analyysikohtaisesti; puuttumismekanismia ei päätelty.",
        "lim_public": "Tätä julkista esittelyä ei ole hyväksytty luottamuksellisten, kliinisten tai säänneltyjen tietojen käsittelyyn.",
        "generated": "Luotu UTC-aikana: {timestamp}.",
        "repro_missing": "Alkuperäiset puuttuvat arvot raportoidaan erillään ei-äärellisten lukujen poissulkemisesta.",
        "repro_charts": "Kuviot käyttävät kaikkia soveltuvia tietoja; hajontakuvion näyttöotos käyttää kiinteää satunnaissiementä ja enintään 5 000 pistettä.",
        "repro_settings": "Raporttityyppi: {report_type}; kohderyhmä: {audience}; laajuus: {depth}.",
        "parsing": "Tiedoston jäsennys: {notes}", "xlsx_parse": "Laskentataulukko: {sheet}. Lopun tyhjä täyte ohitettiin ja aineiston sisäiset tyhjät rivit säilytettiin.", "formula_parse": "Kaavasolut käyttävät työkirjaan tallennettuja tuloksia, jotka voivat olla vanhentuneita tai puuttua; kaavoja ei suoritettu.", "link_parse": "Ulkoisten työkirjojen linkkejä ei ladattu.", "csv_parse": "CSV-merkistökoodaus: {encoding}; erotin: {separator}; desimaalimerkki: {decimal}.", "omitted": "Kuviokiintiön vuoksi pois jäivät: {labels}.",
        "group_note": "Kaikki havaitut ryhmät säilytetään.",
        "scatter_note": "Näytetään enintään 5 000 pistettä kiinteällä satunnaissiemenellä; analyysi käyttää kaikkia soveltuvia pareja.",
        "change_note": "Muutos on loppu- miinus alkumittaus; suuntaa ei tulkita paranemiseksi.",
        "time_note": "Saman päivän havainnot yhdistetään keskiarvolla ja lukumäärällä; interpolointia ei käytetä.",
        "category_limit": "Frekvenssitaulukot rajattiin ensimmäiseen 20 soveltuvaan luokkamuuttujaan; täydet yhteenvedot säilyvät validoidussa analyysiobjektissa.",
    },
}


def _loc(language: Language, key: str, **kwargs: object) -> str:
    value = REPORT_TEXT[language][key]
    return value.format(**kwargs) if kwargs else value


def _role_label(language: Language, role: str) -> str:
    labels = {
        "en": {"identifier": "identifier", "numeric": "numeric", "categorical": "categorical", "ordinal": "ordinal", "date": "date", "text": "text"},
        "zh-CN": {"identifier": "标识符", "numeric": "数值", "categorical": "分类", "ordinal": "有序", "date": "日期", "text": "文本"},
        "es": {"identifier": "identificador", "numeric": "numérico", "categorical": "categórico", "ordinal": "ordinal", "date": "fecha", "text": "texto"},
        "fi": {"identifier": "tunniste", "numeric": "numeerinen", "categorical": "luokka", "ordinal": "järjestysasteikko", "date": "päivämäärä", "text": "teksti"},
    }
    return labels[language].get(role, role)


def _setting_label(language: Language, value: str) -> str:
    labels = {
        "en": {"automatic": "automatic", "descriptive": "descriptive", "data_quality": "data quality", "group": "group comparison", "relationships": "relationships", "change": "change", "time": "date series", "researcher": "researcher", "educator": "educator", "business": "business/management", "general": "general audience", "brief": "brief", "standard": "standard", "detailed": "detailed"},
        "zh-CN": {"automatic": "自动", "descriptive": "描述性", "data_quality": "数据质量", "group": "组间比较", "relationships": "变量关系", "change": "前后变化", "time": "日期序列", "researcher": "研究人员", "educator": "教育工作者", "business": "商业/管理", "general": "一般读者", "brief": "简要", "standard": "标准", "detailed": "详细"},
        "es": {"automatic": "automático", "descriptive": "descriptivo", "data_quality": "calidad de datos", "group": "comparación de grupos", "relationships": "relaciones", "change": "cambio", "time": "serie por fecha", "researcher": "investigación", "educator": "educación", "business": "empresa/gestión", "general": "público general", "brief": "breve", "standard": "estándar", "detailed": "detallado"},
        "fi": {"automatic": "automaattinen", "descriptive": "kuvaileva", "data_quality": "aineiston laatu", "group": "ryhmävertailu", "relationships": "yhteydet", "change": "muutos", "time": "aikasarja", "researcher": "tutkija", "educator": "kouluttaja", "business": "liiketoiminta/johto", "general": "yleinen yleisö", "brief": "lyhyt", "standard": "tavallinen", "detailed": "laaja"},
    }
    return labels[language].get(value, value)


def _localized_parsing_notes(parsed: ParsedData, language: Language) -> str:
    if parsed.selected_sheet:
        return " ".join([
            _loc(language, "xlsx_parse", sheet=parsed.selected_sheet),
            _loc(language, "formula_parse"),
            _loc(language, "link_parse"),
        ])
    note = parsed.notes[0] if parsed.notes else ""
    if note.startswith("CSV encoding: "):
        fields = note.removesuffix(".").split("; ")
        values = [field.split(": ", 1)[1] for field in fields]
        if len(values) == 3:
            return _loc(language, "csv_parse", encoding=values[0], separator=values[1], decimal=values[2])
    return note


class ReportSettings(StrictModel):
    language: Language = "en"
    report_type: ReportType = "automatic"
    audience: Literal["researcher", "educator", "business", "general"] = "researcher"
    depth: Literal["brief", "standard", "detailed"] = "standard"
    study_title: str = Field(default="", max_length=200)
    study_context: str = Field(default="", max_length=2000)
    sections: list[Literal["overview", "quality", "descriptive", "figures", "interpretation"]] = Field(default_factory=lambda: ["overview", "quality", "descriptive", "figures", "interpretation"])
    role_overrides: dict[str, VariableRole] = Field(default_factory=dict)
    label_overrides: dict[str, str] = Field(default_factory=dict)
    units: dict[str, str] = Field(default_factory=dict)
    valid_ranges: dict[str, tuple[float | None, float | None]] = Field(default_factory=dict)
    outcome: str | None = None
    group: str | None = None
    independent_groups: bool = False
    relationship_first: str | None = None
    relationship_second: str | None = None
    pre: str | None = None
    post: str | None = None
    paired_confirmed: bool = False
    date_variable: str | None = None
    time_outcome: str | None = None
    manual_chart_kind: str | None = None
    ai_enabled: bool = False
    share_labels: bool = False
    model: str = DEFAULT_MODEL


@dataclass
class PipelineOutput:
    analysis: AnalysisResult
    report: ReportDocument
    ai_attempts: int = 0
    ai_error: str | None = None


def _numeric_sentence(language: Language, label: str, row: dict[str, object]) -> str:
    values = dict(label=label, n=row["n"], mean=format_number(row["mean"]), sd=format_number(row["sd"]), median=format_number(row["median"]), minimum=format_number(row["min"]), maximum=format_number(row["max"]))
    templates = {
        "en": "For {label}, finite valid observations numbered {n}; M = {mean}, SD = {sd}, median = {median}, minimum = {minimum}, and maximum = {maximum}.",
        "zh-CN": "变量“{label}”共有 {n} 个有限有效观测；M = {mean}，SD = {sd}，中位数 = {median}，最小值 = {minimum}，最大值 = {maximum}。",
        "es": "Para {label} hubo {n} observaciones válidas finitas; M = {mean}, DE = {sd}, mediana = {median}, mínimo = {minimum} y máximo = {maximum}.",
        "fi": "Muuttujalla {label} oli {n} äärellistä kelvollista havaintoa; KA = {mean}, KH = {sd}, mediaani = {median}, minimi = {minimum} ja maksimi = {maximum}.",
    }
    return templates[language].format(**values)


def _dataset_sentence(language: Language, rows: int, columns: int) -> str:
    templates = {
        "en": "The dataset contains {rows} records and {columns} variables.",
        "zh-CN": "该数据集包含 {rows} 条记录和 {columns} 个变量。",
        "es": "El conjunto contiene {rows} registros y {columns} variables.",
        "fi": "Aineistossa on {rows} havaintoa ja {columns} muuttujaa.",
    }
    return templates[language].format(rows=rows, columns=columns)


def _missing_sentence(language: Language, label: str, missing: int, percent: float) -> str:
    templates = {
        "en": "{label} has {missing} originally missing values ({percent:.1f}% of all records).",
        "zh-CN": "变量“{label}”有 {missing} 个原始缺失值（占全部记录的 {percent:.1f}%）。",
        "es": "{label} tiene {missing} valores originalmente faltantes ({percent:.1f}% de todos los registros).",
        "fi": "Muuttujasta {label} puuttuu alun perin {missing} arvoa ({percent:.1f}% kaikista havainnoista).",
    }
    return templates[language].format(label=label, missing=missing, percent=percent)


def _chart_labels(language: Language, kind: str, labels: list[str]) -> tuple[str, str, str]:
    titles = {
        "en": {"histogram": "Distribution of {a}", "bar": "Frequency of {a}", "missingness": "Missingness by variable", "box": "{a} by {b}", "scatter": "{a} and {b}", "paired": "Paired means: {a} and {b}", "date_line": "Date-level mean of {b}"},
        "zh-CN": {"histogram": "{a} 的分布", "bar": "{a} 的频数", "missingness": "各变量缺失率", "box": "按 {b} 分组的 {a}", "scatter": "{a} 与 {b}", "paired": "配对均值：{a} 与 {b}", "date_line": "{b} 的日期层面均值"},
        "es": {"histogram": "Distribución de {a}", "bar": "Frecuencia de {a}", "missingness": "Datos faltantes por variable", "box": "{a} por {b}", "scatter": "{a} y {b}", "paired": "Medias pareadas: {a} y {b}", "date_line": "Media por fecha de {b}"},
        "fi": {"histogram": "Muuttujan {a} jakauma", "bar": "Muuttujan {a} frekvenssit", "missingness": "Puuttuvat tiedot muuttujittain", "box": "{a} ryhmittäin: {b}", "scatter": "{a} ja {b}", "paired": "Parittaiset keskiarvot: {a} ja {b}", "date_line": "Muuttujan {b} päivätason keskiarvo"},
    }
    a = labels[0] if labels else ""
    b = labels[1] if len(labels) > 1 else ""
    title = titles[language][kind].format(a=a, b=b)
    if kind == "missingness":
        return title, t(language, "missing_pct"), t(language, "variable")
    if kind in {"histogram", "bar"}:
        return title, a, t(language, "count")
    return title, a, b


def _table(id_: str, title: str, columns: list[str], rows: list[list[object]], note: str | None = None) -> TableBlock:
    return TableBlock(id=id_, title=title, columns=columns, rows=[[str(value) for value in row] for row in rows], note=note)


def _require(settings: ReportSettings, *names: str) -> None:
    missing = [name for name in names if not getattr(settings, name)]
    if missing:
        raise AnalysisError("Complete the required advanced selectors before generating this report: " + ", ".join(missing) + ".")


def generate_report(
    parsed: ParsedData,
    settings: ReportSettings,
    *,
    gemini_api_key: str = "",
    gemini_paid_service: bool = False,
    session_ai_attempts: int = 0,
) -> PipelineOutput:
    rename_map = {source: label.strip() for source, label in settings.label_overrides.items() if source in parsed.data.columns and label.strip() and label.strip() != source}
    resulting_labels = [rename_map.get(label, label) for label in parsed.data.columns]
    if len(set(resulting_labels)) != len(resulting_labels):
        raise AnalysisError("Display labels must remain unique.")
    data = parsed.data.rename(columns=rename_map).copy()
    language = settings.language
    column_ids = {rename_map.get(label, label): column_id for label, column_id in parsed.column_ids.items()}
    role_overrides = {rename_map.get(label, label): role for label, role in settings.role_overrides.items()}
    columns = infer_roles(data, column_ids, role_overrides)
    units = {rename_map.get(label, label): unit.strip() for label, unit in settings.units.items() if unit.strip()}
    valid_ranges = {rename_map.get(label, label): bounds for label, bounds in settings.valid_ranges.items()}

    def display_label(label: str) -> str:
        return f"{label} ({units[label]})" if label in units else label

    label_to_meta = {column.label: column for column in columns}
    id_to_label = {column.id: display_label(column.label) for column in columns}
    rows, column_count = data.shape
    duplicates = int(data.duplicated().sum())
    constants = [column.label for column in columns if column.unique_nonmissing <= 1]
    id_duplicates = [column.label for column in columns if column.role == "identifier" and data[column.label].dropna().duplicated().any()]
    range_findings: dict[str, int] = {}
    range_sentences: list[str] = []
    for label, (minimum, maximum) in valid_ranges.items():
        if label not in label_to_meta or label_to_meta[label].role != "numeric":
            continue
        if minimum is not None and maximum is not None and minimum > maximum:
            raise AnalysisError(f"The supplied minimum exceeds the maximum for '{label}'.")
        numeric = pd.to_numeric(data[label], errors="coerce").astype(float)
        finite = numeric[(numeric != float("inf")) & (numeric != float("-inf")) & numeric.notna()]
        outside = ((finite < minimum) if minimum is not None else pd.Series(False, index=finite.index)) | ((finite > maximum) if maximum is not None else pd.Series(False, index=finite.index))
        range_findings[label] = int(outside.sum())
        if range_findings[label]:
            range_sentences.append(_loc(language, "range_finding", label=display_label(label), count=range_findings[label], minimum=format_number(minimum) if minimum is not None else "−∞", maximum=format_number(maximum) if maximum is not None else "∞"))
    facts: list[EvidenceFact] = []
    dataset_fact = EvidenceFact(id="dataset_size", kind="dataset", denominator=int(rows), values={"rows": int(rows), "columns": int(column_count)}, method="row and column count", sentence=_dataset_sentence(language, int(rows), int(column_count)))
    facts.append(dataset_fact)
    for column in columns:
        if column.missing:
            facts.append(EvidenceFact(id=f"missing_{column.id}", kind="missingness", variable_ids=[column.id], denominator=int(rows), values={"missing_n": column.missing, "percent": column.missing / rows * 100}, method="original missing count divided by all records", sentence=_missing_sentence(language, display_label(column.label), column.missing, column.missing / rows * 100)))

    descriptives: list[dict[str, object]] = []
    categorical: list[dict[str, object]] = []
    for column in columns:
        if column.role == "numeric":
            row = numeric_summary(data, column.label)
            descriptives.append(row)
            facts.append(EvidenceFact(id=f"numeric_{column.id}", kind="numeric_descriptive", variable_ids=[column.id], denominator=int(row["n"]), values={key: value for key, value in row.items() if key != "variable"}, method="finite observations; arithmetic mean; sample SD (ddof=1)", sentence=_numeric_sentence(language, display_label(column.label), row)))
        elif column.role in {"categorical", "ordinal"}:
            categorical.append(categorical_summary(data, column.label))

    selected: dict[str, object] = {}
    primary_chart: ChartSpec | None = None
    if settings.report_type == "group":
        _require(settings, "outcome", "group")
        outcome, group = rename_map.get(settings.outcome or "", settings.outcome or ""), rename_map.get(settings.group or "", settings.group or "")
        if outcome not in label_to_meta or label_to_meta[outcome].role != "numeric":
            raise AnalysisError("The selected outcome must be an eligible continuous numeric variable.")
        if group not in label_to_meta or label_to_meta[group].role not in {"categorical", "ordinal"}:
            raise AnalysisError("The selected group must be categorical or ordinal.")
        group_count = data[group].dropna().nunique()
        if not 2 <= group_count <= 20:
            raise AnalysisError("The grouping variable must contain 2–20 observed groups.")
        result = group_statistics_detailed(data, outcome, group)
        if settings.independent_groups and group_count == 2:
            try:
                result["effect"] = cohens_d(data.replace([float("inf"), float("-inf")], pd.NA), outcome, group)
            except AnalysisError as exc:
                result["effect_reason"] = str(exc)
        else:
            result["effect_reason"] = _loc(language, "effect_unavailable")
        selected["group"] = result
        primary_chart = ChartSpec(id="chart_primary_group", kind="box", variable_ids=[label_to_meta[outcome].id, label_to_meta[group].id], title="", x_label=group, y_label=outcome, valid_n=int(result["valid_n"]), notes=[_loc(language, "group_note")])
    elif settings.report_type == "relationships":
        _require(settings, "relationship_first", "relationship_second")
        first, second = rename_map.get(settings.relationship_first or "", settings.relationship_first or ""), rename_map.get(settings.relationship_second or "", settings.relationship_second or "")
        if any(name not in label_to_meta or label_to_meta[name].role != "numeric" for name in (first, second)):
            raise AnalysisError("Relationship variables must be distinct eligible continuous numeric variables.")
        result = pearson_relationship(data, first, second)
        selected["relationship"] = result
        primary_chart = ChartSpec(id="chart_primary_relationship", kind="scatter", variable_ids=[label_to_meta[first].id, label_to_meta[second].id], title="", x_label=first, y_label=second, valid_n=int(result["n"]), sampling=_loc(language, "scatter_note"))
    elif settings.report_type == "change":
        _require(settings, "pre", "post")
        if not settings.paired_confirmed:
            raise AnalysisError("Confirm that each row represents the same unit at both occasions.")
        pre, post = rename_map.get(settings.pre or "", settings.pre or ""), rename_map.get(settings.post or "", settings.post or "")
        if any(name not in label_to_meta or label_to_meta[name].role != "numeric" for name in (pre, post)):
            raise AnalysisError("Pre and post must be distinct eligible continuous numeric variables.")
        result = paired_change_statistics(data, pre, post)
        selected["change"] = result
        primary_chart = ChartSpec(id="chart_primary_change", kind="paired", variable_ids=[label_to_meta[pre].id, label_to_meta[post].id], title="", x_label="Occasion", y_label=t(language, "mean"), valid_n=int(result["paired_n"]), notes=[_loc(language, "change_note")])
    elif settings.report_type == "time":
        _require(settings, "date_variable", "time_outcome")
        date_label, outcome = rename_map.get(settings.date_variable or "", settings.date_variable or ""), rename_map.get(settings.time_outcome or "", settings.time_outcome or "")
        if date_label not in label_to_meta or label_to_meta[date_label].role != "date":
            raise AnalysisError("Select a confirmed date variable.")
        if outcome not in label_to_meta or label_to_meta[outcome].role != "numeric":
            raise AnalysisError("Select an eligible numeric outcome.")
        result = date_mean_series(data, date_label, outcome)
        selected["time"] = result
        primary_chart = ChartSpec(id="chart_primary_time", kind="date_line", variable_ids=[label_to_meta[date_label].id, label_to_meta[outcome].id], title="", x_label=date_label, y_label=outcome, valid_n=int(result["valid_n"]), notes=[_loc(language, "time_note")])

    if primary_chart:
        labels = [id_to_label[column_id] for column_id in primary_chart.variable_ids]
        title, x_label, y_label = _chart_labels(language, primary_chart.kind, labels)
        primary_chart = primary_chart.model_copy(update={"title": title, "x_label": x_label, "y_label": y_label})
    chart_specs, omitted_charts = select_charts(data, columns, depth=settings.depth, primary=primary_chart, manual_kind=settings.manual_chart_kind)
    localized_specs: list[ChartSpec] = []
    for spec in chart_specs:
        labels = [id_to_label.get(column_id, column_id) for column_id in spec.variable_ids]
        title, x_label, y_label = _chart_labels(language, spec.kind, labels)
        localized_specs.append(spec.model_copy(update={"title": title, "x_label": x_label, "y_label": y_label}))
    chart_specs = localized_specs

    overview_table = _table("overview_variables", t(language, "overview"), [t(language, "variable"), t(language, "role"), t(language, "valid_n"), t(language, "missing_n")], [[display_label(column.label), _role_label(language, column.role) + (" ?" if column.role_uncertain else ""), column.nonmissing, column.missing] for column in columns])
    quality_columns = [t(language, "variable"), t(language, "missing_n"), t(language, "missing_pct"), t(language, "excluded_n")]
    if valid_ranges:
        quality_columns.append(_loc(language, "outside_range"))
    quality_table = _table("quality_missing", t(language, "quality"), quality_columns, [[display_label(column.label), column.missing, f"{column.missing / rows * 100:.1f}", column.nonfinite] + ([range_findings.get(column.label, 0)] if valid_ranges else []) for column in columns])
    numeric_table = _table("numeric_descriptives", t(language, "descriptive"), [t(language, "variable"), t(language, "valid_n"), t(language, "mean"), t(language, "sd"), t(language, "median"), t(language, "minimum"), t(language, "maximum")], [[display_label(str(row["variable"])), row["n"], format_number(row["mean"]), format_number(row["sd"]), format_number(row["median"]), format_number(row["min"]), format_number(row["max"])] for row in descriptives], _loc(language, "finite_note"))
    categorical_tables: list[TableBlock] = []
    for summary in categorical[:20]:
        category_rows = []
        categories = summary["categories"]
        for index, category in enumerate(categories):
            label = t(language, "other") if summary["aggregated"] and index == len(categories) - 1 else category["label"]
            category_rows.append([label, category["count"], f"{category['percent']:.1f}"])
        categorical_tables.append(_table(
            f"categorical_{len(categorical_tables) + 1}",
            _loc(language, "category_title", label=display_label(str(summary["variable"]))),
            [t(language, "category"), t(language, "count"), t(language, "percent")],
            category_rows,
            _loc(language, "category_note", n=summary["valid_n"]),
        ))

    sections: list[ReportSection] = [
        ReportSection(id="executive", heading=t(language, "executive"), paragraphs=[dataset_fact.sentence, t(language, "descriptive_only")]),
        ReportSection(id="overview", heading=t(language, "overview"), paragraphs=[dataset_fact.sentence, _loc(language, "roles_review")], tables=[overview_table]),
        ReportSection(id="quality", heading=t(language, "quality"), paragraphs=[t(language, "no_missing") if not any(column.missing for column in columns) else " ".join(fact.sentence for fact in facts if fact.kind == "missingness"), _loc(language, "quality_summary", duplicates=duplicates, constants=", ".join(constants) if constants else _loc(language, "none"), id_duplicates=", ".join(id_duplicates) if id_duplicates else _loc(language, "none")), *range_sentences], tables=[quality_table]),
    ]
    if descriptives or categorical_tables:
        descriptive_paragraphs = [fact.sentence for fact in facts if fact.kind == "numeric_descriptive"]
        if categorical_tables:
            descriptive_paragraphs.append(_loc(language, "category_intro"))
        sections.append(ReportSection(id="descriptive", heading=t(language, "descriptive"), paragraphs=descriptive_paragraphs, tables=([numeric_table] if descriptives else []) + categorical_tables))
    else:
        sections.append(ReportSection(id="descriptive", heading=t(language, "descriptive"), paragraphs=[t(language, "no_numeric")]))
    if selected:
        primary_paragraphs: list[str] = []
        primary_tables: list[TableBlock] = []
        if "group" in selected:
            result = selected["group"]
            primary_tables.append(_table("group_summary", t(language, "primary"), [t(language, "group"), t(language, "valid_n"), t(language, "mean"), t(language, "sd"), t(language, "median"), t(language, "minimum"), t(language, "maximum")], [[row["group"], row["n"], format_number(row["mean"]), format_number(row["sd"]), format_number(row["median"]), format_number(row["min"]), format_number(row["max"])] for row in result["rows"]]))
            if result.get("effect"):
                effect = result["effect"]
                direction = f"{effect['group_1']} minus {effect['group_2']}"
                sentence = _loc(language, "effect", direction=direction, difference=format_number(effect["mean_difference"]), effect=format_number(effect["cohens_d"]))
                fact = EvidenceFact(id="group_difference_1", kind="group_difference", denominator=int(result["valid_n"]), values={"mean_difference": float(effect["mean_difference"]), "cohens_d": float(effect["cohens_d"])}, method="complete finite cases; pooled sample SD", direction=direction, sentence=sentence, allowed_interpretation_codes=["describe_direction"])
                facts.append(fact); primary_paragraphs.append(sentence)
            else:
                primary_paragraphs.append(str(result.get("effect_reason")))
        elif "relationship" in selected:
            result = selected["relationship"]
            sentence = _loc(language, "relationship", first=result["first"], second=result["second"], n=result["n"], r=format_number(result["r"])) if result["r"] is not None else _loc(language, "relationship_unavailable", reason=result["reason"], n=result["n"])
            facts.append(EvidenceFact(id="relationship_1", kind="relationship", denominator=int(result["n"]), values={"r": result["r"], "pairwise_n": int(result["n"])}, method="Pearson product-moment correlation on pairwise finite observations", sentence=sentence, allowed_interpretation_codes=["linear_association"] if result["r"] is not None else [])); primary_paragraphs.append(sentence)
        elif "change" in selected:
            result = selected["change"]; change = result["change_summary"]
            sentence = _loc(language, "change", n=result["paired_n"], mean=format_number(change["mean"]), sd=format_number(change["sd"]), median=format_number(change["median"]))
            facts.append(EvidenceFact(id="change_1", kind="paired_change", denominator=int(result["paired_n"]), values={"paired_n": int(result["paired_n"]), "mean": change["mean"], "sd": change["sd"], "median": change["median"]}, method="post minus pre on identical finite pairs", direction="post_minus_pre", sentence=sentence, allowed_interpretation_codes=["describe_direction"])); primary_paragraphs.append(sentence)
        elif "time" in selected:
            result = selected["time"]
            sentence = _loc(language, "time", n=result["valid_n"])
            facts.append(EvidenceFact(id="time_1", kind="date_series", denominator=int(result["valid_n"]), values={"valid_n": int(result["valid_n"]), "dates": len(result["points"])}, method="mean by confirmed date", sentence=sentence)); primary_paragraphs.append(sentence)
        sections.append(ReportSection(id="primary", heading=t(language, "primary"), paragraphs=primary_paragraphs, tables=primary_tables))

    figures = [FigureBlock(id=spec.id, title=spec.title, caption=_loc(language, "valid_caption", title=spec.title, n=spec.valid_n, notes=" ".join(spec.notes + ([spec.sampling] if spec.sampling else []))), alt_text=_loc(language, "alt", kind=spec.kind, title=spec.title, n=spec.valid_n), png=render_chart(spec, data, columns), source_fact_ids=spec.source_fact_ids) for spec in chart_specs]
    if figures:
        sections.append(ReportSection(id="figures", heading=t(language, "figures"), paragraphs=[_loc(language, "figure_intro", number=index, title=figure.title) for index, figure in enumerate(figures, 1)], figures=figures))

    limitations = [t(language, "descriptive_only"), _loc(language, "lim_roles"), _loc(language, "lim_missing"), _loc(language, "lim_public")]
    reproducibility = [
        f"App {APP_VERSION}; schema {SCHEMA_VERSION}; prompt {PROMPT_VERSION}.",
        _loc(language, "generated", timestamp=datetime.now(timezone.utc).isoformat()),
        _loc(language, "repro_missing"),
        _loc(language, "repro_charts"),
        _loc(language, "repro_settings", report_type=_setting_label(language, settings.report_type), audience=_setting_label(language, settings.audience), depth=_setting_label(language, settings.depth)),
        _loc(language, "parsing", notes=_localized_parsing_notes(parsed, language)),
    ]
    if omitted_charts:
        reproducibility.append(_loc(language, "omitted", labels=", ".join(omitted_charts)))
    if len(categorical) > len(categorical_tables):
        reproducibility.append(_loc(language, "category_limit"))
    sections.extend([
        ReportSection(id="interpretation", heading=t(language, "interpretation"), paragraphs=[_loc(language, "interpretation_text")]),
        ReportSection(id="limitations", heading=t(language, "limitations"), paragraphs=limitations),
        ReportSection(id="technical", heading=t(language, "technical"), paragraphs=[t(language, "decimal_note"), *reproducibility]),
    ])

    mode: Literal["template", "ai_assisted"] = "template"
    status_note = t(language, "template_status")
    ai_attempts = 0
    ai_error: str | None = None
    if settings.ai_enabled:
        payload, transmitted_ids = build_ai_payload(facts, language=language, audience=settings.audience, depth=settings.depth, study_context=settings.study_context, share_labels=settings.share_labels)
        narrative, returned_model, ai_error, ai_attempts = request_validated_narrative(facts, payload, GeminiConfig(api_key=gemini_api_key, model=settings.model, paid_service=gemini_paid_service, session_attempts=session_ai_attempts))
        reproducibility.append(f"Gemini requested model: {settings.model}; returned model: {returned_model or 'unavailable'}; selected fact IDs: {', '.join(transmitted_ids) or 'none'}; requests counted: {ai_attempts}.")
        if narrative:
            target = next(section for section in sections if section.id == "interpretation")
            target.paragraphs = [expand_fact_tokens(block.prose, facts) for block in narrative.blocks]
            mode = "ai_assisted"; status_note = t(language, "ai_status")
        else:
            status_note = t(language, "fallback")

    selected_section_ids = set(settings.sections)
    if settings.ai_enabled:
        selected_section_ids.add("interpretation")
    required_section_ids = {"executive", "primary", "limitations", "technical"}
    sections = [section for section in sections if section.id in required_section_ids or section.id in selected_section_ids]

    analysis = AnalysisResult(schema_version=SCHEMA_VERSION, language=language, report_type=settings.report_type, rows=int(rows), columns=int(column_count), column_metadata=columns, settings=settings.model_dump(mode="json"), parsing_notes=parsed.notes, quality={"duplicate_rows": duplicates, "constant_variables": constants, "possible_identifier_duplicates": id_duplicates, "outside_user_ranges": range_findings}, descriptives=descriptives + categorical, selected_analyses=selected, limitations=limitations, facts=facts, chart_specs=chart_specs, reproducibility=reproducibility)
    report = ReportDocument(schema_version=SCHEMA_VERSION, language=language, title=settings.study_title.strip() or t(language, "title"), subtitle=t(language, "subtitle"), mode=mode, status_note=status_note, generated_at_utc=datetime.now(timezone.utc), sections=sections, facts=facts, reproducibility=reproducibility)
    return PipelineOutput(analysis=analysis, report=report, ai_attempts=ai_attempts, ai_error=ai_error)
