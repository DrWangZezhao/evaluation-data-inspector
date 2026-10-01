"""Four-language interface labels and deterministic factual templates."""

from __future__ import annotations

from .models import Language


LANGUAGE_OPTIONS = {"English": "en", "简体中文": "zh-CN", "Español": "es", "Suomi": "fi"}


TEXT: dict[Language, dict[str, str]] = {
    "en": {
        "subtitle": "From evaluation data to transparent, evidence-based reports.",
        "upload": "Upload CSV or Excel",
        "language": "Report language",
        "generate": "Generate report",
        "advanced": "Advanced settings",
        "try_sample": "Try synthetic example",
        "clear": "Clear data",
        "privacy": "Files are processed in session memory and are not intentionally persisted by this app. Hosting infrastructure may retain operational data; do not upload confidential records.",
        "ready": "Ready: {rows} records × {columns} variables. Roles are inferred, not verified.",
        "invalid": "The file is not ready for reporting: {message}",
        "sheet": "Worksheet",
        "encoding": "CSV encoding",
        "separator": "CSV separator",
        "decimal": "Decimal mark",
        "report_type": "Report type",
        "audience": "Audience",
        "depth": "Depth",
        "study_title": "Optional study title",
        "context": "Optional study context",
        "ai": "AI-assisted writing",
        "ai_unavailable": "AI writing is unavailable until the operator configures a billing-linked Gemini service. Template reports remain fully available.",
        "ai_disclosure": "When enabled, up to 30 selected aggregate facts and optional context are sent to Google Gemini. Raw rows, IDs, filenames, and text cells are not sent. This minimization is not a guarantee of anonymization.",
        "labels": "Share reviewed labels/context with Gemini",
        "outcome": "Numeric outcome",
        "group": "Grouping variable",
        "independent": "Confirm groups are independent (required for Cohen's d)",
        "x_variable": "First numeric variable",
        "y_variable": "Second numeric variable",
        "pre": "Pre variable",
        "post": "Post variable",
        "paired": "Confirm each row represents the same unit at both occasions",
        "date": "Date variable",
        "download_docx": "Download DOCX",
        "download_html": "Download HTML",
        "print_note": "Open the downloaded HTML in a browser and use Print → Save as PDF. Pagination and client fonts may vary.",
        "template_status": "Template report",
        "ai_status": "AI-assisted report",
        "fallback": "AI writing was unavailable or invalid; the complete deterministic template report was used.",
        "title": "Evaluation Data Inspector",
        "executive": "Executive Summary",
        "overview": "Dataset Overview",
        "quality": "Data Quality",
        "descriptive": "Descriptive Results",
        "primary": "Primary Analysis",
        "figures": "Figures",
        "interpretation": "Interpretation",
        "limitations": "Limitations",
        "technical": "Technical Notes",
        "rows": "Records",
        "columns": "Variables",
        "duplicates": "Duplicate rows",
        "variable": "Variable",
        "role": "Role",
        "valid_n": "Valid n",
        "missing_n": "Missing n",
        "missing_pct": "Missing (%)",
        "excluded_n": "Non-finite excluded",
        "mean": "M",
        "sd": "SD",
        "median": "Median",
        "minimum": "Minimum",
        "maximum": "Maximum",
        "category": "Category",
        "count": "Count",
        "percent": "Percent of valid observations",
        "other": "Other",
        "figure": "Figure",
        "table": "Table",
        "no_numeric": "No eligible continuous numeric variables were identified; quality and structure are still reported.",
        "no_missing": "No original missing cells were identified.",
        "formula_note": "Formula cells use cached workbook results, which may be stale or absent; formulas are never evaluated.",
        "descriptive_only": "All analyses are descriptive. No hypothesis tests, p values, confidence intervals, causal effects, or missingness mechanisms were estimated.",
        "decimal_note": "Statistical values use a decimal point in every report language. Counts are integers; percentages use one decimal; most statistics use two decimals.",
    },
    "zh-CN": {
        "subtitle": "从评估数据生成透明、基于证据的报告。", "upload": "上传 CSV 或 Excel", "language": "报告语言", "generate": "生成报告", "advanced": "高级设置", "try_sample": "试用合成示例", "clear": "清除数据",
        "privacy": "文件仅在当前会话内存中处理，本应用不会有意持久化。托管基础设施可能保留运行数据；请勿上传机密记录。", "ready": "已就绪：{rows} 条记录 × {columns} 个变量。变量角色为推断结果，尚未经人工确认。", "invalid": "文件尚不能生成报告：{message}", "sheet": "工作表", "encoding": "CSV 编码", "separator": "CSV 分隔符", "decimal": "小数符号", "report_type": "报告类型", "audience": "受众", "depth": "详细程度", "study_title": "可选研究标题", "context": "可选研究背景", "ai": "AI 辅助写作",
        "ai_unavailable": "运营者配置与计费关联的 Gemini 服务后才可使用 AI 写作；模板报告始终可用。", "ai_disclosure": "启用后，最多 30 条经筛选的汇总事实和可选背景将发送给 Google Gemini。原始行、标识符、文件名和文本单元格不会发送。此最小化措施不构成匿名化保证。", "labels": "向 Gemini 共享经审阅的标签/背景", "outcome": "数值结果变量", "group": "分组变量", "independent": "确认组间独立（计算 Cohen's d 的必要条件）", "x_variable": "第一个数值变量", "y_variable": "第二个数值变量", "pre": "前测变量", "post": "后测变量", "paired": "确认每一行表示同一对象在两个时间点的记录", "date": "日期变量", "download_docx": "下载 DOCX", "download_html": "下载 HTML", "print_note": "在浏览器中打开下载的 HTML，使用“打印 → 另存为 PDF”。分页和客户端字体可能不同。", "template_status": "模板报告", "ai_status": "AI 辅助报告", "fallback": "AI 写作不可用或输出未通过验证，已使用完整的确定性模板报告。",
        "title": "评估数据检查器", "executive": "执行摘要", "overview": "数据集概览", "quality": "数据质量", "descriptive": "描述性结果", "primary": "主要分析", "figures": "图形", "interpretation": "解释", "limitations": "局限性", "technical": "技术说明", "rows": "记录数", "columns": "变量数", "duplicates": "重复行", "variable": "变量", "role": "角色", "valid_n": "有效 n", "missing_n": "缺失 n", "missing_pct": "缺失（%）", "excluded_n": "排除的非有限值", "mean": "M", "sd": "SD", "median": "中位数", "minimum": "最小值", "maximum": "最大值", "category": "类别", "count": "计数", "percent": "占有效观测的百分比", "other": "其他", "figure": "图", "table": "表", "no_numeric": "未识别出符合条件的连续数值变量；报告仍包含数据质量与结构信息。", "no_missing": "未发现原始缺失单元格。", "formula_note": "公式单元格使用工作簿缓存结果，可能过期或缺失；本应用不会执行公式。", "descriptive_only": "所有分析均为描述性分析。未估计假设检验、p 值、置信区间、因果效应或缺失机制。", "decimal_note": "所有报告语言中的统计值均使用小数点。计数为整数，百分比保留一位小数，大多数统计量保留两位小数。",
    },
    "es": {
        "subtitle": "De los datos de evaluación a informes transparentes basados en evidencia.", "upload": "Cargar CSV o Excel", "language": "Idioma del informe", "generate": "Generar informe", "advanced": "Configuración avanzada", "try_sample": "Probar ejemplo sintético", "clear": "Borrar datos", "privacy": "Los archivos se procesan en la memoria de la sesión y la aplicación no los conserva intencionadamente. La infraestructura puede retener datos operativos; no cargue registros confidenciales.", "ready": "Listo: {rows} registros × {columns} variables. Los roles se infieren; no están verificados.", "invalid": "El archivo no está listo: {message}", "sheet": "Hoja", "encoding": "Codificación CSV", "separator": "Separador CSV", "decimal": "Marca decimal", "report_type": "Tipo de informe", "audience": "Audiencia", "depth": "Extensión", "study_title": "Título opcional", "context": "Contexto opcional", "ai": "Redacción asistida por IA", "ai_unavailable": "La IA requiere que el operador configure Gemini con facturación. Los informes de plantilla siguen disponibles.", "ai_disclosure": "Al activarla, se envían a Google Gemini hasta 30 resultados agregados y el contexto opcional. No se envían filas, identificadores, nombres de archivo ni celdas de texto. Esto no garantiza anonimización.", "labels": "Compartir etiquetas/contexto revisados con Gemini", "outcome": "Resultado numérico", "group": "Variable de grupo", "independent": "Confirmar grupos independientes (necesario para d de Cohen)", "x_variable": "Primera variable numérica", "y_variable": "Segunda variable numérica", "pre": "Variable pre", "post": "Variable post", "paired": "Confirmar que cada fila representa la misma unidad en ambas ocasiones", "date": "Variable de fecha", "download_docx": "Descargar DOCX", "download_html": "Descargar HTML", "print_note": "Abra el HTML en un navegador y use Imprimir → Guardar como PDF. La paginación y las fuentes pueden variar.", "template_status": "Informe de plantilla", "ai_status": "Informe asistido por IA", "fallback": "La IA no estuvo disponible o no superó la validación; se usó el informe determinista completo.", "title": "Inspector de Datos de Evaluación", "executive": "Resumen ejecutivo", "overview": "Descripción del conjunto", "quality": "Calidad de los datos", "descriptive": "Resultados descriptivos", "primary": "Análisis principal", "figures": "Figuras", "interpretation": "Interpretación", "limitations": "Limitaciones", "technical": "Notas técnicas", "rows": "Registros", "columns": "Variables", "duplicates": "Filas duplicadas", "variable": "Variable", "role": "Rol", "valid_n": "n válido", "missing_n": "n faltante", "missing_pct": "Faltante (%)", "excluded_n": "No finitos excluidos", "mean": "M", "sd": "DE", "median": "Mediana", "minimum": "Mínimo", "maximum": "Máximo", "category": "Categoría", "count": "Frecuencia", "percent": "Porcentaje de observaciones válidas", "other": "Otros", "figure": "Figura", "table": "Tabla", "no_numeric": "No se identificaron variables numéricas continuas elegibles; se informa la calidad y estructura.", "no_missing": "No se identificaron celdas originalmente faltantes.", "formula_note": "Las fórmulas usan resultados almacenados en el libro, que pueden estar desactualizados o ausentes; no se evalúan fórmulas.", "descriptive_only": "Todos los análisis son descriptivos. No se estimaron pruebas de hipótesis, valores p, intervalos de confianza, efectos causales ni mecanismos de ausencia.", "decimal_note": "Los valores estadísticos usan punto decimal en todos los idiomas. Los recuentos son enteros, los porcentajes tienen un decimal y la mayoría de estadísticas dos.",
    },
    "fi": {
        "subtitle": "Arviointiaineistosta läpinäkyväksi, näyttöön perustuvaksi raportiksi.", "upload": "Lataa CSV- tai Excel-tiedosto", "language": "Raportin kieli", "generate": "Luo raportti", "advanced": "Lisäasetukset", "try_sample": "Kokeile synteettistä esimerkkiä", "clear": "Tyhjennä tiedot", "privacy": "Tiedostot käsitellään istunnon muistissa, eikä sovellus tarkoituksellisesti tallenna niitä. Isännöintipalvelu voi säilyttää käyttötietoja; älä lataa luottamuksellisia tietoja.", "ready": "Valmis: {rows} havaintoa × {columns} muuttujaa. Muuttujien roolit on päätelty, ei varmennettu.", "invalid": "Tiedosto ei ole valmis raportointiin: {message}", "sheet": "Laskentataulukko", "encoding": "CSV-merkistökoodaus", "separator": "CSV-erotin", "decimal": "Desimaalimerkki", "report_type": "Raporttityyppi", "audience": "Kohderyhmä", "depth": "Laajuus", "study_title": "Valinnainen tutkimuksen otsikko", "context": "Valinnainen tutkimuskonteksti", "ai": "Tekoälyavusteinen kirjoittaminen", "ai_unavailable": "Tekoäly edellyttää, että ylläpitäjä määrittää laskutukseen liitetyn Gemini-palvelun. Malliraportit ovat aina käytettävissä.", "ai_disclosure": "Kun toiminto on käytössä, Google Geminille lähetetään enintään 30 valittua koontitietoa ja valinnainen konteksti. Raakarivejä, tunnisteita, tiedostonimiä tai tekstisoluja ei lähetetä. Tämä ei takaa anonymiteettiä.", "labels": "Jaa tarkistetut nimet/konteksti Geminille", "outcome": "Numeerinen tulosmuuttuja", "group": "Ryhmittelymuuttuja", "independent": "Vahvista ryhmien riippumattomuus (Cohenin d:n edellytys)", "x_variable": "Ensimmäinen numeerinen muuttuja", "y_variable": "Toinen numeerinen muuttuja", "pre": "Alkumittausmuuttuja", "post": "Loppumittausmuuttuja", "paired": "Vahvista, että kukin rivi kuvaa samaa yksikköä molemmilla mittauskerroilla", "date": "Päivämäärämuuttuja", "download_docx": "Lataa DOCX", "download_html": "Lataa HTML", "print_note": "Avaa HTML selaimessa ja valitse Tulosta → Tallenna PDF-muodossa. Sivutus ja fontit voivat vaihdella.", "template_status": "Malliraportti", "ai_status": "Tekoälyavusteinen raportti", "fallback": "Tekoäly ei ollut käytettävissä tai vastaus ei läpäissyt tarkistusta; käytettiin täydellistä determinististä malliraporttia.", "title": "Arviointiaineiston tarkastin", "executive": "Tiivistelmä", "overview": "Aineiston yleiskuva", "quality": "Aineiston laatu", "descriptive": "Kuvailevat tulokset", "primary": "Pääanalyysi", "figures": "Kuviot", "interpretation": "Tulkinta", "limitations": "Rajoitukset", "technical": "Tekniset tiedot", "rows": "Havainnot", "columns": "Muuttujat", "duplicates": "Päällekkäiset rivit", "variable": "Muuttuja", "role": "Rooli", "valid_n": "Kelvollinen n", "missing_n": "Puuttuva n", "missing_pct": "Puuttuva (%)", "excluded_n": "Poissuljetut ei-äärelliset", "mean": "KA", "sd": "KH", "median": "Mediaani", "minimum": "Minimi", "maximum": "Maksimi", "category": "Luokka", "count": "Lukumäärä", "percent": "Osuus kelvollisista havainnoista", "other": "Muut", "figure": "Kuvio", "table": "Taulukko", "no_numeric": "Soveltuvia jatkuvia numeerisia muuttujia ei tunnistettu; aineiston laatu ja rakenne raportoidaan silti.", "no_missing": "Alun perin puuttuvia soluja ei havaittu.", "formula_note": "Kaavasolut käyttävät työkirjaan tallennettuja tuloksia, jotka voivat olla vanhentuneita tai puuttua; kaavoja ei suoriteta.", "descriptive_only": "Kaikki analyysit ovat kuvailevia. Hypoteesitestejä, p-arvoja, luottamusvälejä, kausaalivaikutuksia tai puuttumismekanismeja ei arvioitu.", "decimal_note": "Tilastollisissa arvoissa käytetään desimaalipistettä kaikilla raporttikielillä. Lukumäärät ovat kokonaislukuja, prosentit esitetään yhdellä ja useimmat tunnusluvut kahdella desimaalilla.",
    },
}


def t(language: Language, key: str, **kwargs: object) -> str:
    value = TEXT[language].get(key, TEXT["en"].get(key, key))
    return value.format(**kwargs) if kwargs else value


def format_number(value: float | int | None, decimals: int = 2) -> str:
    if value is None:
        return "—"
    if isinstance(value, int):
        return str(value)
    if value != 0 and abs(value) < 10 ** (-decimals):
        return f"{value:.3e}"
    return f"{value:.{decimals}f}"
