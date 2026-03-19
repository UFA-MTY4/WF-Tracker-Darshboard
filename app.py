import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
from pathlib import Path
from PIL import Image
import io
import os
from datetime import datetime as dt  # para timestamp en backups

# =========================
# CONFIGURE THE PAGE
# =========================
try:
    icono = Image.open("SE.PNG")
except Exception:
    icono = None

st.set_page_config(
    page_title="WF Tracker MTY4",
    page_icon=icono,
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================
# FORMATING
# =========================
GREEN = "#22D947"
BG_COLOR = "#0E1117"

st.markdown(f"""
<style>
.stApp {{ background-color:{BG_COLOR}; color:white; }}
section[data-testid="stSidebar"] {{ background-color:#161A22; }}

.stTextInput>div>div>input,
.stSelectbox>div>div,
.stMultiSelect>div>div,
.stDateInput>div>div {{
    background-color:#1C1F26 !important;
    color:white !important;
    border:none !important;
}}

[data-baseweb="tag"] {{
    background-color:{GREEN} !important;
    color:black !important;
}}

.stButton>button {{
    background-color:{GREEN};
    color:black;
    border:none;
    font-weight:600;
}}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* Centrar valores y etiquetas de KPI */
[data-testid="stMetricValue"],
[data-testid="stMetricLabel"] {
    justify-content: center !important;
    text-align: center !important;
}

/* Tarjeta de KPI con borde verde y fondo acorde */
div[data-testid="metric-container"] {
    background-color: #1C1F26 !important;
    padding: 15px 5px !important;
    border-radius: 10px !important;
    border: 2px solid #22D947 !important;  /* borde verde */
    text-align: center !important;
    align-items: center !important;
    box-shadow: 0px 0px 8px rgba(34, 217, 71, 0.25); /* glow suave */
}
</style>
""", unsafe_allow_html=True)

# =========================
# MAIN HEADER
# =========================
col1, col2, col3 = st.columns([0.2,1,0.2])

with col1:
    if icono:
        st.image(icono, width=180)

with col2:
    st.markdown(
        "<h1 style='text-align:center;font-weight:900;'>WorkFlow Tracker Analytics (2025-2026)</h1>",
        unsafe_allow_html=True
    )

with col3:
    st.write(f"Last updated:\n{datetime.now().strftime('%d %B %Y')}")

# =========================
# DATA BASE CALLOUT
# =========================
route = Path("WF pendientes.xlsx")
sheet = "Database PZ4 + SWBD"

# BACKUP AND DATA BASE OVERWRITING USING OTHER EXCEL
def backup_file(src_path: Path) -> Path | None:
    """Crea backup con timestamp en ./backups y regresa la ruta del backup, o None si no existe src."""
    if not src_path.exists():
        return None
    backups_dir = Path("backups")
    backups_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.now().strftime("%Y%m%d_%H%M%S")
    bkp_path = backups_dir / f"{src_path.stem}_backup_{stamp}{src_path.suffix}"
    src_path.replace(bkp_path)  # mueve el original al backup
    return bkp_path

def overwrite_excel_from_upload(uploaded_bytes: bytes, dest_path: Path):
    """Escribe los bytes subidos en la ruta destino."""
    with open(dest_path, "wb") as f:
        f.write(uploaded_bytes)

# =========================
# LOADING (USING CACHE)
# =========================
@st.cache_data
def cargar_excel(path, sheet):
    return pd.read_excel(path, engine="openpyxl", sheet_name=sheet)

# =========================
# SIDEBAR UPDATE DATABASE
# =========================
st.sidebar.header("Filters")

# UPLOAD FILE TO OVERWRITE
with st.sidebar.expander("⚙️ UPDATE DATABASE (Overwrite Excel)", expanded=False):
    st.caption(
        "Upload a new WF pendientes **.xlsx** with the same structure."
        "**An automatic backup** will be created and the data base will be overwriten."
    )
    uploaded_file = st.file_uploader(
        "Select Excel (.xlsx)",
        type=["xlsx"],
        help="Data base must contain 'Database PZ4 + SWBD' and column of date.",
        key="uploader"
    )

    # VALIDATION
    if uploaded_file is not None:
        # READ THE MEMORY AND VALIDATE
        try:
            # READ MEMORY
            content = uploaded_file.read()
            memfile = io.BytesIO(content)
            df_test = pd.read_excel(memfile, engine="openpyxl", sheet_name=sheet)

            # VALIDATE START DATE COLUMN
            startdate = ["Start date","Start Date","start date","START DATE"]
            col_fecha_tmp = next((c for c in startdate if c in df_test.columns), None)

            if col_fecha_tmp is None:
                st.error(
                    "❌ El archivo no tiene ninguna de las columnas de fecha esperadas: "
                    f"{', '.join(startdate)}"
                )
            else:
                # Hacemos backup del archivo actual (si existe) moviéndolo a /backups
                bkp_path = backup_file(route)  # mueve el original al backup
                # Escribimos el nuevo archivo en la ruta original
                overwrite_excel_from_upload(content, route)

                # Limpiamos caché de datos para que el dashboard recargue desde el nuevo archivo
                st.cache_data.clear()

                st.success("File uploaded and dashboard updated.")
                if bkp_path:
                    with open(bkp_path, "rb") as bkp_f:
                        st.download_button(
                            "Download previous backup",
                            data=bkp_f,
                            file_name=bkp_path.name,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                st.info("Refresh the page (Ctrl+R) if data is not updated.")
        except Exception as e:
            st.error(f"❌ No se pudo procesar el archivo subido: {e}")

# =========================
# CARGA BASE
# =========================
# Si no existe el archivo (p.ej. primera vez), mostrar aviso
if not route.exists():
    st.error(
        f"Data base file as not being found '{route.name}'. "
        "Upload a Data base file in the side bar."
    )
    st.stop()

df = cargar_excel(route, sheet)


# =========================
# DATE COLUMN
# =========================
startdate = ["Start date","Start Date","start date","START DATE"]
col_fecha = next((c for c in startdate if c in df.columns), None)

if not col_fecha:
    st.error(
        "No column with the name start date was found: "
        f"{', '.join(startdate)}"
    )
    st.stop()

df[col_fecha] = pd.to_datetime(df[col_fecha], errors="coerce")

# Convertir RM a datetime si existe
if "RM" in df.columns:
    df["RM"] = pd.to_datetime(df["RM"], errors="coerce")

# =========================
# NORMALIZING
# =========================
for c in ["Type", "Class", "Status", "Product"]:
    if c in df.columns:
        df[c] = df[c].astype(str).str.upper().str.strip() if c != "Product" else df[c].astype(str).str.strip()

df_global = df.copy()

# Column Name (for re usage)
col_clasif = "Classification [Completion-Due Date]"

# =========================
# FILTER OPTIONS
# =========================
today = date.today()
first_day_month = today.replace(day=1)

type_options = ["BUY","MAKE","CNG-BOM","OBS"] if "Type" in df.columns else []
class_options = sorted(df["Class"].dropna().unique()) if "Class" in df.columns else []
status_options = ["I","C","X"] if "Status" in df.columns else []
product_options = sorted(df["Product"].dropna().unique()) if "Product" in df.columns else []

for key, default in {
    "fecha_inicio": first_day_month,
    "fecha_fin": today,
    "sales": "",
    "job": "",
    "type": type_options,
    "class_sel": class_options,
    "status": status_options,
    "product_sel": product_options
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

def reset_filters():
    st.session_state.fecha_inicio = first_day_month
    st.session_state.fecha_fin = today
    st.session_state.sales = ""
    st.session_state.job = ""
    st.session_state.type = type_options
    st.session_state.class_sel = class_options
    st.session_state.status = status_options
    st.session_state.product_sel = product_options

st.sidebar.button("Reset Filters", on_click=reset_filters)

# Filtro de fecha principal
fecha_inicio, fecha_fin = st.sidebar.date_input(
    "Start Date range",
    (st.session_state.fecha_inicio, st.session_state.fecha_fin)
)

# === RM DATE RANGE FILTER ===
if "RM" in df.columns:
    rm_min = df["RM"].min()
    rm_max = df["RM"].max()

    rm_inicio, rm_fin = st.sidebar.date_input(
        "RM Date Range",
        (rm_min, rm_max)
    )
else:
    rm_inicio = rm_fin = None

# Otros filtros
sales_filter = st.sidebar.text_input("Sales Number", key="sales")
job_filter = st.sidebar.text_input("Job Name", key="job")
type_sel = st.sidebar.multiselect("Type", type_options, key="type")
class_sel = st.sidebar.multiselect("Class", class_options, key="class_sel")
status_sel = st.sidebar.multiselect("Status", status_options, key="status")
product_sel = st.sidebar.multiselect("Product", product_options, key="product_sel")


# =========================
# FILTERED DATAFRAME
# =========================
mask_fecha = (
    (df[col_fecha] >= pd.to_datetime(fecha_inicio)) &
    (df[col_fecha] <= pd.to_datetime(fecha_fin))
)

# === MASK RM ===
mask_rm = True
if "RM" in df.columns and rm_inicio and rm_fin:
    mask_rm = (
        (df["RM"] >= pd.to_datetime(rm_inicio)) &
        (df["RM"] <= pd.to_datetime(rm_fin))
    )

df_filtered = df.loc[
    mask_fecha &
    mask_rm &
    (df["Type"].isin(type_sel) if "Type" in df.columns else True) &
    (df["Class"].isin(class_sel) if "Class" in df.columns else True) &
    (df["Status"].isin(status_sel) if "Status" in df.columns else True) &
    (df["Product"].isin(product_sel) if "Product" in df.columns else True)
].copy()

if sales_filter and "Sales Number" in df_filtered.columns:
    df_filtered = df_filtered[
        df_filtered["Sales Number"].astype(str)
        .str.contains(sales_filter, case=False, na=False)
    ]

if job_filter and "Job Name" in df_filtered.columns:
    df_filtered = df_filtered[
        df_filtered["Job Name"].astype(str)
        .str.contains(job_filter, case=False, na=False)
    ]

# =========================
# CARDS ROW 1
# =========================
colA, colB, colC = st.columns(3)
colA.metric("Total WF (Global)", len(df_global))
colB.metric("Total WF (Filtered)", len(df_filtered))

completion_rate = (
    (df_filtered["Status"] == "C").mean() * 100
    if ("Status" in df_filtered.columns and not df_filtered.empty) else 0
)
colC.metric("Completion Rate (Filtered)", f"{completion_rate:.2f}%")

# =========================
# CARDS ROW 2
# =========================
pct_cancelados_global = (
    (df_global["Status"] == "X").mean() * 100
    if ("Status" in df_global.columns and not df_global.empty) else 0
)
activos_global = int((df_global["Status"] == "I").sum()) if ("Status" in df_global.columns and not df_global.empty) else 0


# =========================
# LATE BY ENG COUNT (Filtered)
# =========================

# Inicializar
late_filtered = 0

# Detectar columna real del WF SUBMITTAL, tolerando HTML escapado
wf_submit_candidates = [
    "WF SUBMITTAL [RM<5/10 DAYS]",
    "WF SUBMITTAL [RM&lt;5/10 DAYS]"
]
col_wf_submit_real = next((c for c in wf_submit_candidates if c in df_filtered.columns), None)

# Contar valores LATE BY ENG
if not df_filtered.empty:

    if col_wf_submit_real:
        # Normalización del texto
        serie = (
            df_filtered[col_wf_submit_real]
            .astype(str)
            .str.upper()
            .str.strip()
        )

        # Contamos si contiene "LATE BY ENG"
        late_filtered = int(
            serie.str.contains(r"\bLATE BY ENG\b", na=False).sum()
        )

    # Fallback si WF SUBMITTAL no existe pero sí la clasificación
    elif col_clasif in df_filtered.columns:
        serie = (
            df_filtered[col_clasif]
            .astype(str)
            .str.upper()
            .str.strip()
        )
        late_filtered = int((serie == "LATE BY ENG").sum())

# =========================
# KPI CARDS
# =========================
colD, colE, colF = st.columns(3)

colD.metric("Canceled WF % (Global)", f"{pct_cancelados_global:.2f}%")
colE.metric("Active WF (Global)", f"{activos_global}")
colF.metric("Late WF - LATE BY ENG (Filtered)", f"{late_filtered}")


# =========================
# FILTERED ANALYTICS
# =========================
st.markdown("## 📊 Filtered Analytics")

if not df_filtered.empty:

    if "Job Name" in df_filtered.columns:
        resumen_job = (
            df_filtered.groupby("Job Name")
            .size()
            .reset_index(name="WorkFlows")
            .sort_values("WorkFlows", ascending=False)
        )

        fig_job = px.bar(
            resumen_job,
            x="Job Name",
            y="WorkFlows",
            title="WF Distribution by Job Name (Filtered)",
            color_discrete_sequence=[GREEN]
        )

        fig_job.update_layout(
            plot_bgcolor=BG_COLOR,
            paper_bgcolor=BG_COLOR,
            font_color="white",
            xaxis_tickangle=-45
        )

        st.plotly_chart(fig_job, use_container_width=True)

    # FILTERED RING GRAPHS
    if col_clasif in df_filtered.columns or "Class" in df_filtered.columns:
        c1, c2 = st.columns(2)

        # COL 1: RING - Classification (Filtered)
        if col_clasif in df_filtered.columns:
            resumen_class_filtered = (
                df_filtered.groupby(col_clasif)
                .size()
                .reset_index(name="WorkFlows")
            )

            with c1:
                fig_class_filtered = px.pie(
                    resumen_class_filtered,
                    names=col_clasif,
                    values="WorkFlows",
                    title="Classification [Completion-Due Date] (Filtered)",
                    color_discrete_sequence=[GREEN],
                    hole=0.5
                )
                fig_class_filtered.update_layout(
                    plot_bgcolor=BG_COLOR,
                    paper_bgcolor=BG_COLOR,
                    font_color="white"
                )
                st.plotly_chart(fig_class_filtered, use_container_width=True)

        # COL 2: RING - Class (Filtered)
        if "Class" in df_filtered.columns:
            resumen_class_filtered_ring = (
                df_filtered.groupby("Class")
                .size()
                .reset_index(name="WorkFlows")
                .sort_values("WorkFlows", ascending=False)
            )

            with c2:
                fig_class_ring_filtered = px.pie(
                    resumen_class_filtered_ring,
                    names="Class",
                    values="WorkFlows",
                    title="WF Distribution by Class (Filtered)",
                    hole=0.5,
                    color_discrete_sequence=[GREEN]
                )
                fig_class_ring_filtered.update_layout(
                    plot_bgcolor=BG_COLOR,
                    paper_bgcolor=BG_COLOR,
                    font_color="white",
                    showlegend=True
                )
                st.plotly_chart(fig_class_ring_filtered, use_container_width=True)


# =========================
# IMPACTED JOBS & Average Time Metrics (Filtered)
# =========================
st.markdown("## Projects Impacted (Filtered) & Average Time Metrics (Filtered)")

# Nombres de columnas según tu dataset
col_impacted = "Impacted Post RM"
col_wf_submit = "WF SUBMITTAL [RM<5/10 DAYS]"
col_job = "Job Name"
col_status = "Status"

# Validar columnas requeridas
required_cols = [col_job, col_impacted, col_wf_submit, col_clasif, col_status]
missing = [c for c in required_cols if c not in df_filtered.columns]

if missing:
    st.info(
        "Data could not be extracted, graph cannot be created: "
        + ", ".join(missing)
    )
else:
    # Masks  (case-insensitive)
    impacted_mask = df_filtered[col_impacted].astype(str).str.contains("IMPACTED", case=False, na=False)

    late_by_eng_mask = df_filtered[col_wf_submit].astype(str).str.contains("LATE BY ENG", case=False, na=False)
    ontime_by_eng_mask = df_filtered[col_wf_submit].astype(str).str.contains("ON TIME BY ENG", case=False, na=False)

    # Classification LATE (case-insensitive)
    late_class_mask = df_filtered[col_clasif].astype(str).str.strip().str.upper().eq("LATE")

    # Contar Job Names únicos
    def unique_jobs_count(df_sub):
        if col_job not in df_sub.columns:
            return 0
        return (
            df_sub[col_job]
            .astype(str).str.strip()
            .replace("", pd.NA)
            .dropna()
            .nunique()
        )

    # 1) IMPACTED + LATE BY ENG
    df_impact_late = df_filtered[impacted_mask & late_by_eng_mask]
    n_impact_late = unique_jobs_count(df_impact_late)

    # 2) LATE (Classification)
    df_late_class = df_filtered[late_class_mask]
    n_late_class = unique_jobs_count(df_late_class)

    # 3) IMPACTED + ON TIME BY ENG
    df_impact_ontime = df_filtered[impacted_mask & ontime_by_eng_mask]
    n_impact_ontime = unique_jobs_count(df_impact_ontime)

    # Crear DataFrame para la gráfica
    df_chart = pd.DataFrame({
        "Category": [
            "IMPACTED + LATE BY ENG",
            "LATE (Template)",
            "IMPACTED + ON TIME BY ENG"
        ],
        "Projects": [
            n_impact_late,
            n_late_class,
            n_impact_ontime
        ]
    })
    

# =========================
# 📊 Average Time Metrics (Filtered) — Solo LATE y SUPER LATE
# =========================

# Columnas objetivo
time_columns = [
    "Pre RM Opening Time",
    "Overdue Time [Expected-Completion]",
    "Active Time"
]

classification_col = "Classification [Completion-Due Date]"

avg_df = None  # Inicializamos para controlar el flujo

# 1) Validar columna de clasificación
if classification_col not in df_filtered.columns:
    st.info("⚠️ La columna 'Classification [Completion-Due Date]' no existe en el dataset filtrado.")
else:
    # 2) Filtrar LATE y SUPER LATE (tolerante a espacios y mayúsculas)
    mask_late = (
        df_filtered[classification_col]
        .astype(str).str.strip().str.upper()
        .isin(["LATE", "SUPER LATE"])
    )
    df_late = df_filtered[mask_late]

    if df_late.empty:
        st.info("ℹ️ No hay filas con clasificación 'LATE' o 'SUPER LATE' en el dataset filtrado.")
    else:
        # 3) Verificar columnas de tiempo existentes en el subset filtrado
        valid_time_cols = [c for c in time_columns if c in df_late.columns]

        if not valid_time_cols:
            st.info("⚠️ No time-related columns available in the LATE/SUPER LATE subset.")
        else:
            # 4) Asegurar conversión numérica
            df_time = df_late[valid_time_cols].apply(pd.to_numeric, errors="coerce")

            # 5) Calcular promedios y redondear a 2 decimales
            avg_df = df_time.mean().round(2).reset_index()
            avg_df.columns = ["Metric", "Average"]

            # 6) Mostrar tabla en Streamlit
            st.subheader("Average Time Metrics (LATE & SUPER LATE)")
            st.dataframe(avg_df)

# 7) Graficar si hay datos


# =========================
# HORIZONTAL BAR CHARTS (2 columnas)
# =========================
ca, cb = st.columns(2)

with ca:
    # Validamos que df_chart exista y tenga datos
    if 'df_chart' in locals() and not df_chart.empty:
        fig_unique_jobs = px.bar(
            df_chart.sort_values("Projects", ascending=True),
            x="Projects",
            y="Category",
            orientation="h",
            title="Job Names by Impact/Late Conditions (Filtered)",
            text="Projects",
            color="Projects",
            color_continuous_scale="Reds",
        )

        fig_unique_jobs.update_traces(textposition="outside")

        fig_unique_jobs.update_layout(
            plot_bgcolor=BG_COLOR,
            paper_bgcolor=BG_COLOR,
            font_color="white",
            xaxis_title="Projects",
            yaxis_title="Condition",
            margin=dict(l=20, r=20, t=60, b=20)
        )

        st.plotly_chart(fig_unique_jobs, use_container_width=True)
    else:
        st.info("There is no data for the graph Impact/Late Conditions.")
with cb:
if avg_df is not None and not avg_df.empty:
    fig_time = px.bar(
        avg_df.sort_values("Average"),
        x="Average",
        y="Metric",
        orientation="h",
        title="Average Time Metrics (LATE & SUPER LATE)",
        text="Average",
        color="Average",
        color_continuous_scale="Greens"
    )

    fig_time.update_traces(textposition="outside")

    fig_time.update_layout(
        plot_bgcolor=BG_COLOR,
        paper_bgcolor=BG_COLOR,
        font_color="white",
        xaxis_title="Average (Days)",
        yaxis_title="Metric",
        margin=dict(l=20, r=20, t=40, b=20)
    )

    st.plotly_chart(fig_time, use_container_width=True)
else:
    st.info("There is no data for the graph Average Time Metrics (LATE & SUPER LATE).")



# =========================
# 2-COLUMN LAYOUT: Treemap (left) + Detail Selector (right)
# =========================
st.markdown("## 🗂️ WF per Task Responsible (Filtered)")

# DETECTAR COLUMNA 'Task responsible' (robusto)
# =========================
col_responsable = None

for col in df_filtered.columns:
    if col.strip().lower() == "task responsible".lower():
        col_responsable = col
        break
    
col_left, col_right = st.columns([1.3, 1])

if col_responsable is not None and col_responsable in df_filtered.columns:

    # ==========================================
    # LEFT COLUMN → TREEMAP
    # ==========================================
    with col_left:

        resumen_responsible = (
            df_filtered.groupby(col_responsable)
            .size()
            .reset_index(name="WorkFlows")
        )

        fig_responsible_tree = px.treemap(
            resumen_responsible,
            path=[col_responsable],
            values="WorkFlows",
            title="Treemap of WF per Task Responsible",
            color="WorkFlows",
            color_continuous_scale="Greens"
        )

        fig_responsible_tree.update_layout(
            plot_bgcolor=BG_COLOR,
            paper_bgcolor=BG_COLOR,
            font_color="white"
        )

        st.plotly_chart(fig_responsible_tree, use_container_width=True)

    # ==========================================
    # RIGHT COLUMN → SELECTOR + DETAIL VIEW
    # ==========================================
    with col_right:

        st.markdown("### Select Task Responsible to view details")

        selected_resp = st.selectbox(
            "Task Responsible:",
            resumen_responsible[col_responsable].sort_values().unique(),
            index=None,
            placeholder="Select a responsible..."
        )

        if selected_resp:
            st.markdown(f"### WorkFlows for **{selected_resp}**")

            df_detail = df_filtered[df_filtered[col_responsable] == selected_resp]

            with st.expander(f"Show WF assigned to {selected_resp}", expanded=True):
                st.dataframe(df_detail, use_container_width=True)

else:
    st.info("Task responsible column was not found.")

# =========================
# GLOBAL ANALYTICS
# =========================
st.markdown("---")
st.markdown("## 🌍 Global Analytics")

# Month labels (text) y columns for order
df_global["Month"] = df_global[col_fecha].dt.strftime("%B")
df_global["YearMonth"] = df_global[col_fecha].dt.to_period("M").dt.to_timestamp()

resumen_global = (
    df_global.groupby("YearMonth")
    .size()
    .reset_index(name="WorkFlows")
    .sort_values("YearMonth")  # asegura orden cronológico
)

# Line graph
fig_global_month = px.line(
    resumen_global,
    x="YearMonth",
    y="WorkFlows",
    title="WF per Month (Global)",
    line_shape="spline",
)
fig_global_month.update_traces(
    mode="lines+markers",
    line=dict(color=GREEN, width=3),
    marker=dict(color="red", size=8)
)
fig_global_month.update_layout(
    plot_bgcolor=BG_COLOR,
    paper_bgcolor=BG_COLOR,
    font_color="white",
    xaxis_title="Month",
    yaxis_title="WorkFlows"
)
st.plotly_chart(fig_global_month, use_container_width=True)

# =========================
# OTHER GLOBAL
# =========================
# RING - STATUS (Global)
if "Status" in df_global.columns:
    resumen_status = (
        df_global.groupby("Status")
        .size()
        .reset_index(name="WorkFlows")
    )

    fig_global_status = px.pie(
        resumen_status,
        names="Status",
        values="WorkFlows",
        title="WF Distribution by Status (Global)",
        color_discrete_sequence=[GREEN],
        hole=0.5
    )

    fig_global_status.update_layout(
        plot_bgcolor=BG_COLOR,
        paper_bgcolor=BG_COLOR,
        font_color="white"
    )
else:
    fig_global_status = None

# RING - Classification (Global)
fig_class_global = None
if col_clasif in df_global.columns:
    resumen_class_global = (
        df_global.groupby(col_clasif)
        .size()
        .reset_index(name="WorkFlows")
    )

    fig_class_global = px.pie(
        resumen_class_global,
        names=col_clasif,
        values="WorkFlows",
        title="Classification [Completion-Due Date] (Global)",
        color_discrete_sequence=[GREEN],
        hole=0.5
    )

    fig_class_global.update_layout(
        plot_bgcolor=BG_COLOR,
        paper_bgcolor=BG_COLOR,
        font_color="white"
    )

col_d1, col_d2 = st.columns(2)

with col_d1:
    if fig_global_status:
        st.plotly_chart(fig_global_status, use_container_width=True)
    else:
        st.info("No está disponible la columna 'Status' en df_global.")

with col_d2:
    if fig_class_global:
        st.plotly_chart(fig_class_global, use_container_width=True)
    else:
        st.info("Classification [Completion-Due Date] no está disponible en df_global.")

# =========================
# ⚠️ Critical WorkFlows
# =========================

st.markdown("## ⚠️ Critical WorkFlows")

st.error("Notify PMDA team for support on critical WorkFlows impacting RM dates")

# Base principal
_df_base = df_filtered if not df_filtered.empty else df

# ===============================
# 🗓 Formatear RM como YYYY-MM-DD
# ===============================
if "RM" in _df_base.columns:
    _df_base["RM"] = pd.to_datetime(_df_base["RM"], errors="coerce").dt.strftime("%Y-%m-%d")

# ==================================================
# ➕ Agregar columna % Of completion si no existe
# ==================================================
if "% Of completion" not in _df_base.columns:
    _df_base["% Of completion"] = None

# ===============================
#     Critical Workflows Logic
# ===============================
if "Urgent Closure" in _df_base.columns:

    df_critical = _df_base.copy()
    df_critical["Urgent Closure"] = pd.to_numeric(df_critical["Urgent Closure"], errors="coerce")

    # Filtrar >= -5
    df_critical = df_critical[df_critical["Urgent Closure"] >= -5]

    cols_target = ["Sales Number", "Job Name", "WF", "RM", "% Of completion"]
    cols_existentes = [c for c in cols_target if c in df_critical.columns]

    if not df_critical.empty and cols_existentes:

        # Ordenar por urgencia
        df_critical = df_critical.sort_values("Urgent Closure", ascending=True)

        st.caption(f"Showing {len(df_critical)} registers with Urgent Closure ≥ -5")

        # Estilo rojo + negritas
        def highlight_cols(val):
            return "color: red; font-weight: bold"

        styler = df_critical[cols_existentes].style.applymap(
            highlight_cols, subset=["Job Name", "RM"]
        )

        st.dataframe(styler, use_container_width=True)

    else:
        st.info("There is no critical WorkFlows within the period selected.")
else:
    st.warning("La columna 'Urgent Closure' no está presente en el dataset.")

# =========================
#       Filtered Table
# =========================
st.subheader("Filtered Data")
st.dataframe(_df_base, use_container_width=True)
