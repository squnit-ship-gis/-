import streamlit as st
import os
import zipfile
import tempfile
import geopandas as gpd
from streamlit_folium import st_folium
import folium


# دالة عرض الطبقة على خريطة
def show_map(layer_data, map_key, color):
    if layer_data is None or layer_data.empty:
        return

    map_layer = layer_data.to_crs(epsg=4326)
    center = map_layer.geometry.unary_union.centroid

    my_map = folium.Map(
        location=[center.y, center.x],
        zoom_start=11,
        tiles="CartoDB positron"
    )

    folium.GeoJson(
        map_layer,
        style_function=lambda x: {
            "fillColor": color,
            "color": "#222222",
            "weight": 2,
            "fillOpacity": 0.45
        } if x["geometry"]["type"] != "Point" else {
            "color": color,
            "weight": 4
        }
    ).add_to(my_map)

    st_folium(my_map, width=500, height=320, key=map_key)


# دالة قراءة ملف الشيب فايل المضغوط
def load_left_zip(zip_file):
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, zip_file.name)

    with open(zip_path, "wb") as f:
        f.write(zip_file.getbuffer())

    extract_dir = os.path.join(temp_dir, "left_data")
    os.makedirs(extract_dir, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)

    shp_files = [f for f in os.listdir(extract_dir) if f.endswith(".shp")]
    if not shp_files:
        raise ValueError("ملف ZIP لا يحتوي على Shapefile")

    shp_path = os.path.join(extract_dir, shp_files[0])
    return gpd.read_file(shp_path)


# دالة قراءة ملف الجيوجيسون
def load_right_geojson(geojson_file):
    temp_dir = tempfile.mkdtemp()
    geojson_path = os.path.join(temp_dir, geojson_file.name)

    with open(geojson_path, "wb") as f:
        f.write(geojson_file.getbuffer())

    return gpd.read_file(geojson_path)


st.set_page_config(
    page_title="GIS App",
    layout="wide"
)

st.title("تطبيق ويب ونظم معلومات جغرافية")
st.write("نظام تفاعلي لتنفيذ عمليات الربط المكاني والوصفي")

# الشريط الجانبي
st.sidebar.header("رفع البيانات")

left_file = st.sidebar.file_uploader(
    "ارفع ملف شيب فايل مضغوط (ZIP)",
    type=["zip"]
)

right_file = st.sidebar.file_uploader(
    "ارفع ملف جيجيسون (GeoJSON)",
    type=["geojson", "json"]
)

join_choice = st.sidebar.radio(
    "اختر نوع الربط",
    ["Spatial Join", "Attribute Join"]
)

# رسائل نجاح رفع الملفات
if left_file is not None:
    st.success("تم رفع ملف شيب فايل المضغوط بنجاح")

if right_file is not None:
    st.success("تم رفع ملف الجيجيسون بنجاح")

# قراءة الطبقات
left_layer = None
right_layer = None

if left_file is not None:
    try:
        left_layer = load_left_zip(left_file)
        st.success("تمت قراءة طبقة Left بنجاح")
    except Exception as e:
        st.error(f"خطأ في قراءة ملف Left: {e}")

if right_file is not None:
    try:
        right_layer = load_right_geojson(right_file)
        st.success("تمت قراءة طبقة Right بنجاح")
    except Exception as e:
        st.error(f"خطأ في قراءة ملف Right: {e}")

# عرض أول 5 صفوف
col1, col2 = st.columns(2)

with col1:
    st.subheader("الطبقة الأساسية (Left)")
    if left_layer is not None:
        st.dataframe(left_layer.head())

with col2:
    st.subheader("الطبقة الثانوية (Right)")
    if right_layer is not None:
        st.dataframe(right_layer.head())

# عرض الخرائط
map_col1, map_col2 = st.columns(2)

with map_col1:
    st.subheader("الخريطة التفاعلية للطبقة الأساسية")
    if left_layer is not None:
        show_map(left_layer, "left_map", "#4CAF50")

with map_col2:
    st.subheader("الخريطة التفاعلية للطبقة الثانوية")
    if right_layer is not None:
        show_map(right_layer, "right_map", "#E53935")

st.markdown("---")

# تنفيذ العمليات
if left_layer is not None and right_layer is not None:

    # الربط المكاني
    if join_choice == "Spatial Join":
        st.subheader("تنفيذ الربط المكاني")

        spatial_type = st.selectbox(
            "اختر العلاقة المكانية",
            ["within", "intersects", "contains"]
        )

        if st.button("تشغيل الربط المكاني"):
            try:
                with st.spinner("جار تنفيذ العملية..."):
                    spatial_result = gpd.sjoin(
                        right_layer,
                        left_layer,
                        how="left",
                        predicate=spatial_type
                    )

                st.success("تم تنفيذ الربط المكاني بنجاح")
                st.write(f"عدد النتائج: {len(spatial_result)}")

                if spatial_result.empty:
                    st.warning("لا يوجد أي تطابق بين الطبقتين")
                else:
                    st.dataframe(spatial_result.head())

                    geojson_data = spatial_result.to_json()

                    st.download_button(
                        label="تنزيل النتيجة بصيغة GeoJSON",
                        data=geojson_data,
                        file_name="spatial_result.geojson",
                        mime="application/json"
                    )

            except Exception as error:
                st.error(f"حدث خطأ: {error}")

    # الربط الوصفي
    elif join_choice == "Attribute Join":
        st.subheader("تنفيذ الربط الوصفي (Attribute Join)")

        left_column = st.selectbox(
            "اختر الحقل من الطبقة الأساسية",
            list(left_layer.columns)
        )

        right_column = st.selectbox(
            "اختر الحقل من الطبقة الثانوية",
            list(right_layer.columns)
        )

        join_type = st.selectbox(
            "اختر نوع الربط",
            ["left", "right", "inner", "outer"]
        )

        if st.button("تشغيل الربط الوصفي"):
            try:
                with st.spinner("جار تنفيذ العملية..."):
                    attribute_result = right_layer.merge(
                        left_layer,
                        left_on=right_column,
                        right_on=left_column,
                        how=join_type
                    )

                    if "geometry_x" in attribute_result.columns:
                        attribute_result = gpd.GeoDataFrame(
                            attribute_result,
                            geometry="geometry_x"
                        )

                    if "geometry_y" in attribute_result.columns:
                        attribute_result = attribute_result.drop(columns=["geometry_y"])

                st.success("تم تنفيذ الربط الوصفي بنجاح")
                st.write(f"عدد النتائج: {len(attribute_result)}")

                if attribute_result.empty:
                    st.warning("لا يوجد أي تطابق بين الحقول المحددة")
                else:
                    st.dataframe(attribute_result.head())

                    geojson_data = attribute_result.to_json()

                    st.download_button(
                        label="تنزيل النتيجة بصيغة GeoJSON",
                        data=geojson_data,
                        file_name="attribute_result.geojson",
                        mime="application/json"
                    )

            except Exception as error:
                st.error(f"حدث خطأ: {error}")

else:
    st.info("يرجى رفع الملفين أولا حتى تظهر أدوات التنفيذ.")



