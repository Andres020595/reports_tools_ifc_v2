import streamlit as st
import pandas as pd
import tempfile
import io
from ifc_parser import load_ifc_file, get_elements_with_properties
from st_aggrid import AgGrid, GridOptionsBuilder

st.set_page_config(page_title="📊 IFC Multi-Report Tool v2", layout="wide")
st.title("📊 IFC Multi-Report Tool v2")

# Subir varios IFCs
uploaded_files = st.file_uploader("Sube uno o varios archivos IFC", type=["ifc"], accept_multiple_files=True)

if uploaded_files:
    all_dataframes = []

    for uploaded_file in uploaded_files:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name

        ifc_model = load_ifc_file(tmp_path)
        if ifc_model:
            df = get_elements_with_properties(ifc_model)
            if not df.empty:
                df["Archivo_IFC"] = uploaded_file.name
                all_dataframes.append(df)

    if all_dataframes:
        full_df = pd.concat(all_dataframes, ignore_index=True)

        st.subheader("🔍 Explorador de parámetros únicos")
        param_col = st.selectbox("Selecciona un campo para ver sus valores únicos:", options=sorted(full_df.columns))
        unique_values = sorted(full_df[param_col].dropna().unique().tolist())
        st.write(f"**Valores únicos encontrados ({len(unique_values)}):**")
        st.write(unique_values)

        st.divider()

        st.subheader("📑 Selección de columnas para el reporte")

        default_fields = {"GUID", "Name", "Type", "Archivo_IFC"}
        selected_columns = []
        cols_per_row = 3
        cols = st.columns(cols_per_row)

        for idx, column in enumerate(full_df.columns):
            with cols[idx % cols_per_row]:
                checked = st.checkbox(column, value=(column in default_fields))
                if checked:
                    selected_columns.append(column)

        filtered_df = full_df[selected_columns]

        st.subheader("👁️ Vista completa del Excel a exportar")

        # Configurar AgGrid
        gb = GridOptionsBuilder.from_dataframe(filtered_df)
        gb.configure_default_column(resizable=True, sortable=True, filter=True)
        gb.configure_grid_options(domLayout='normal')
        grid_options = gb.build()

        AgGrid(
            filtered_df,
            gridOptions=grid_options,
            height=600,
            fit_columns_on_grid_load=True,
            enable_enterprise_modules=False
        )

        st.divider()

        # Exportar Excel
        buffer = io.BytesIO()
        if st.button("📥 Exportar Excel"):
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                filtered_df.to_excel(writer, index=False, sheet_name="Reporte IFC")
            st.download_button(
                label="Descargar Excel",
                data=buffer.getvalue(),
                file_name="reporte_ifc_multiple.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
