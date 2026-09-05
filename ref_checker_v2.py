import streamlit as st
import re
import pandas as pd
from io import StringIO

# 设置页面布局为宽屏
st.set_page_config(page_title="毕业论文参考文献检查器", layout="wide")
st.title("📚 毕业论文参考文献格式检查器")
st.caption("支持 GB/T 7714-2015 标准 | 适用于本科/硕士毕业论文场景 | 支持批量导入导出")

# ---------- 核心检查函数 ----------
def check_reference(ref_str):
    errors = []
    warnings = []

    if not ref_str.strip():
        return "❌ 输入为空", [], []

    # 1. 检查 [J]
    if "[J]" not in ref_str and "［J］" not in ref_str:
        errors.append("❌ 缺少文献类型标识 [J]")

    # 2. 检查年份
    year_match = re.search(r'\b(19|20)\d{2}\b', ref_str)
    if not year_match:
        errors.append("❌ 缺少4位数字年份")

    # 3. 检查卷号(括号)
    if "(" not in ref_str or ")" not in ref_str:
        warnings.append("⚠️ 建议补充卷号(期号) 如 35(2)")

    # 4. 检查页码
    if ":" in ref_str:
        page_part = ref_str.split(":")[-1].strip()
        if not re.search(r'\d+-\d+', page_part):
            errors.append("❌ 页码格式不规范，应为 起始页-终止页")
    else:
        errors.append("❌ 缺少页码标识冒号 (:)")

    # 5. 判断总体状态
    if not errors and not warnings:
        return "✅ 格式规范", [], []
    elif errors:
        return "❌ 存在错误", errors, warnings
    else:
        return "⚠️ 存在警告", [], warnings

# ---------- 辅助：提取年份 ----------
def extract_year(ref):
    match = re.search(r'\b(19|20)\d{2}\b', ref)
    return int(match.group()) if match else 0

# ---------- 辅助：判断是否英文文献 ----------
def is_english(ref):
    eng_chars = re.findall(r'[a-zA-Z]', ref)
    return len(eng_chars) > 10

# ---------- 界面布局 ----------
# 侧边栏：导入与场景设置
with st.sidebar:
    st.header("⚙️ 场景设置")
    thesis_type = st.radio("选择论文类型", ["本科毕业论文", "硕士/博士学位论文"], index=0)

    if thesis_type == "本科毕业论文":
        min_total = 10
        min_recent = 5
        st.info("📌 要求：总数≥10篇，近3年≥5篇")
    else:
        min_total = 20
        min_recent = 8
        st.info("📌 要求：总数≥20篇，近3年≥8篇")

    st.divider()
    st.header("📂 批量导入")
    uploaded_file = st.file_uploader("上传 .txt 文件 (每行一条)", type=['txt'])

    lines = []
    if uploaded_file is not None:
        stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
        lines = stringio.read().splitlines()
        st.success(f"已读取 {len(lines)} 条文献")

# 主区域
tab1, tab2 = st.tabs(["📝 手动输入 / 批量检查", "📊 结果仪表盘与导出"])

# ---------- Tab 1: 输入与检查 ----------
with tab1:
    col1, col2 = st.columns([2, 1])
    with col1:
        default_text = "\n".join(lines) if lines else ""
        text_input = st.text_area("在此粘贴参考文献（每行一条）", height=300, value=default_text)

    with col2:
        st.write(" ")
        st.write(" ")
        check_btn = st.button("🚀 开始检查", use_container_width=True, type="primary")
        st.caption("支持单条或批量粘贴")

# 存储检查结果到 session_state
if 'results_df' not in st.session_state:
    st.session_state.results_df = None

if check_btn and text_input:
    raw_lines = text_input.strip().split('\n')
    data = []
    for idx, line in enumerate(raw_lines, 1):
        if not line.strip():
            continue
        status, errs, warns = check_reference(line)
        year = extract_year(line)
        eng = is_english(line)
        data.append({
            "序号": idx,
            "参考文献": line,
            "状态": status,
            "错误详情": "；".join(errs) if errs else "无",
            "警告详情": "；".join(warns) if warns else "无",
            "年份": year,
            "是否英文": eng
        })

    st.session_state.results_df = pd.DataFrame(data)
    st.success(f"检查完成！共检查 {len(data)} 条文献。请切换到「结果仪表盘」查看详情。")

# ---------- Tab 2: 结果展示、统计与导出 ----------
with tab2:
    if st.session_state.results_df is not None and not st.session_state.results_df.empty:
        df = st.session_state.results_df

        total = len(df)
        errors = len(df[df['状态'] == '❌ 存在错误'])
        passed = len(df[df['状态'] == '✅ 格式规范'])
        warns = len(df[df['状态'] == '⚠️ 存在警告'])

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📄 总文献数", total)
        col2.metric("✅ 格式通过", passed, delta=f"{passed/total*100:.0f}%" if total > 0 else "0%")
        col3.metric("⚠️ 存在警告", warns)
        col4.metric("❌ 存在错误", errors, delta_color="inverse")

        st.divider()

        st.subheader("🎓 毕业论文参考文献完整性分析")
        recent_count = len(df[df['年份'] >= 2024])
        eng_count = len(df[df['是否英文'] == True])

        check_col1, check_col2, check_col3 = st.columns(3)
        total_ok = total >= min_total
        check_col1.metric(f"总数量要求 (≥{min_total})", f"{total} 篇",
                         delta="✅ 达标" if total_ok else f"❌ 缺 {min_total - total} 篇",
                         delta_color="normal" if total_ok else "inverse")

        recent_ok = recent_count >= min_recent
        check_col2.metric(f"近3年文献 (≥{min_recent})", f"{recent_count} 篇",
                         delta="✅ 达标" if recent_ok else f"❌ 缺 {min_recent - recent_count} 篇",
                         delta_color="normal" if recent_ok else "inverse")

        check_col3.metric("英文文献占比 (建议)", f"{eng_count} 篇",
                         delta="占比适中" if eng_count > total * 0.3 else "建议增加外文文献",
                         delta_color="off" if eng_count > total * 0.3 else "inverse")

        st.divider()

        with st.expander("📋 查看每条文献的详细检查结果", expanded=True):
            st.dataframe(
                df[['序号', '参考文献', '状态', '错误详情']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "状态": st.column_config.TextColumn("检查状态", width="small"),
                    "错误详情": st.column_config.TextColumn("错误信息", width="medium"),
                }
            )

        st.divider()
        st.subheader("📥 导出检查报告")

        csv = df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📎 下载检查报告 (CSV格式，可用Excel打开)",
            data=csv,
            file_name='references_check_report.csv',
            mime='text/csv',
            use_container_width=True,
            type="primary"
        )

        # 新增：导出为 Excel 格式
        from io import BytesIO

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='参考文献检查结果')
        st.download_button(
            label="📊 下载检查报告 (Excel格式，双击直接打开)",
            data=output.getvalue(),
            file_name='references_check_report.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            use_container_width=True,
            type="primary"
        )
        correct_refs = df[df['状态'] == '✅ 格式规范']['参考文献'].tolist()
        if correct_refs:
            txt_data = "\n".join(correct_refs)
            st.download_button(
                label="📝 仅下载格式正确的参考文献 (TXT)",
                data=txt_data,
                file_name='correct_references.txt',
                mime='text/plain',
                use_container_width=True
            )

    else:
        st.info("👆 请在「手动输入」Tab 中点击「开始检查」来查看结果。")

st.divider()
st.caption("💡 使用提示：上传TXT文件可自动导入；检查后可导出CSV报告。年份要求基于2026年当前时间。")