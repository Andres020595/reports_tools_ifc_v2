import streamlit as st
import pandas as pd
import tempfile
import io
from ifc_parser import load_ifc_file, get_elements_with_properties
from st_aggrid import AgGrid, GridOptionsBuilder
from openpyxl import Workbook

# --------------------------------------------------
# CONFIGURACIÓN BÁSICA
# --------------------------------------------------
st.set_page_config(page_title="🧱 Explorador IFC", layout="wide")
st.title("🧱 Explorador IFC")
st.caption("Analiza y exporta propiedades desde archivos IFC")

# --------------------------------------------------
# SUBIDA DE ARCHIVOS
# --------------------------------------------------
uploaded_files = st.file_uploader(
    "📁 Sube uno o varios archivos IFC", 
    type=["ifc"], 
    accept_multiple_files=True
)

# --------------------------------------------------
# PROCESAMIENTO
# --------------------------------------------------
if uploaded_files:
    all_dataframes = []

    for uploaded_file in uploaded_files:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name

        ifc_model = load_ifc_file(tmp_path)
        if ifc_model is not None:
            df = get_elements_with_properties(ifc_model)
            if df is not None and not df.empty:
                df["Archivo_IFC"] = uploaded_file.name
                all_dataframes.append(df)

    if all_dataframes:
        full_df = pd.concat(all_dataframes, ignore_index=True)

        # ----------------------------------------------------------
        # EXPLORADOR DE PARÁMETROS ÚNICOS
        # ----------------------------------------------------------
        st.subheader("🔍 Explorador de parámetros únicos")
        param_col = st.selectbox(
            "Selecciona un campo para analizar:", 
            options=sorted(full_df.columns)
        )

        unique_lists_by_file = {}
        max_len = 0
        for file_name, group in full_df.groupby("Archivo_IFC"):
            vals = sorted(group[param_col].dropna().unique().tolist())
            unique_lists_by_file[file_name] = vals
            if len(vals) > max_len:
                max_len = len(vals)

        # Igualar longitudes
        for file_name, vals in unique_lists_by_file.items():
            if len(vals) < max_len:
                unique_lists_by_file[file_name] = vals + [""] * (max_len - len(vals))

        matrix_df = pd.DataFrame(unique_lists_by_file)

        st.subheader("📁 Valores únicos por archivo IFC")
        gbm = GridOptionsBuilder.from_dataframe(matrix_df)
        gbm.configure_default_column(
            resizable=True, wrapText=True, autoHeight=True, sortable=True, filter=True
        )
        grid_options_m = gbm.build()
        AgGrid(matrix_df, gridOptions=grid_options_m, height=600, fit_columns_on_grid_load=True)

        st.divider()

        # ----------------------------------------------------------
        # SELECCIÓN DE COLUMNAS / PSETS CON CHECKBOXES
        # ----------------------------------------------------------
        st.subheader("👁️ Selección de Psets / Propiedades a exportar")

        columnas_disponibles = [c for c in full_df.columns if c != "Archivo_IFC"]

        if "columnas_seleccionadas" not in st.session_state:
            st.session_state.columnas_seleccionadas = {c: True for c in columnas_disponibles}

        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("✅ Seleccionar todo"):
                for c in columnas_disponibles:
                    st.session_state.columnas_seleccionadas[c] = True
            if st.button("❌ Deseleccionar todo"):
                for c in columnas_disponibles:
                    st.session_state.columnas_seleccionadas[c] = False

        with col2:
            st.markdown("**Selecciona manualmente los campos que deseas incluir:**")
            for c in columnas_disponibles:
                st.session_state.columnas_seleccionadas[c] = st.checkbox(
                    c, value=st.session_state.columnas_seleccionadas[c]
                )

        columnas_finales = [k for k, v in st.session_state.columnas_seleccionadas.items() if v]
        df_filtrado = full_df[["Archivo_IFC"] + columnas_finales]

        # ----------------------------------------------------------
        # VISTA PREVIA
        # ----------------------------------------------------------
        st.divider()
        st.subheader("📋 Vista previa de la exportación filtrada")
        gb = GridOptionsBuilder.from_dataframe(df_filtrado)
        gb.configure_default_column(resizable=True, sortable=True, filter=True)
        grid_options = gb.build()
        AgGrid(df_filtrado, gridOptions=grid_options, height=600, fit_columns_on_grid_load=True)

        st.divider()

        # ----------------------------------------------------------
        # EXPORTACIÓN
        # ----------------------------------------------------------
        st.subheader("📥 Exportar Excel personalizado")
        st.caption("Exporta solo las propiedades seleccionadas.")

        buffer = io.BytesIO()
        if st.button("📥 Exportar Excel filtrado"):
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df_filtrado.to_excel(writer, index=False, sheet_name="Reporte IFC filtrado")
                matrix_df.to_excel(writer, index=False, sheet_name="Valores únicos matriz")

            st.download_button(
                label="⬇️ Descargar Excel filtrado",
                data=buffer.getvalue(),
                file_name="reporte_ifc_filtrado.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

else:
    st.info("Sube uno o varios archivos IFC para comenzar la exploración.")


