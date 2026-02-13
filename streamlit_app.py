import streamlit as st
import pandas as pd
import requests
import os
from datetime import datetime
from pathlib import Path

# --- 配置页面 ---
st.set_page_config(page_title='黄金实时监控看板', page_icon='💰')

DATA_FILENAME = Path(__file__).parent/'gold_history.csv'

# --- 函数定义：获取并保存数据 ---
def update_gold_data():
    """从接口获取数据并追加到本地CSV"""
    url = "https://m.cmbchina.com/api/rate/gold"
    try:
        resp = requests.get(url, timeout=5).json()
        raw_items = resp.get('body', {}).get('data', [])
        update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        new_records = []
        for item in raw_items:
            new_records.append({
                'Time': update_time,
                'Variety': item['variety'],
                'Price': float(item['curPrice']),
                'GoldNo': item['goldNo']
            })
        
        new_df = pd.DataFrame(new_records)
        
        # 如果文件存在则追加，不存在则创建
        if not DATA_FILENAME.exists():
            new_df.to_csv(DATA_FILENAME, index=False)
        else:
            new_df.to_csv(DATA_FILENAME, mode='a', header=False, index=False)
        return True
    except Exception as e:
        st.error(f"数据更新失败: {e}")
        return False

@st.cache_data(ttl=60) # 缓存1分钟，避免频繁读取硬盘
def load_history_data():
    if not DATA_FILENAME.exists():
        # 如果没有数据，先更新一次
        update_gold_data()
    df = pd.read_csv(DATA_FILENAME)
    df['Time'] = pd.to_datetime(df['Time'])
    return df

# --- 执行数据更新 ---
# 每次刷新页面都会尝试抓取最新点位
update_gold_data()
df_all = load_history_data()

# --- 绘制界面 ---
st.title('💰 黄金行情实时监控')
st.markdown(f"最后同步时间: `{df_all['Time'].max()}`")

# 侧边栏过滤
# --- 侧边栏过滤修改版 ---
with st.sidebar:
    st.header("数据筛选")
    varieties = df_all['Variety'].unique()
    selected_varieties = st.multiselect(
        '选择要查看的品种',
        varieties,
        default=varieties[:2] if len(varieties) >= 2 else varieties
    )
    
    # 获取最小和最大时间
    min_t = df_all['Time'].min().to_pydatetime()
    max_t = df_all['Time'].max().to_pydatetime()

    # --- 修复逻辑开始 ---
    # 如果时间相等（只有一条数据），则手动给 min_t 减去 1 分钟，避免报错
    if min_t == max_t:
        from datetime import timedelta
        min_t = max_t - timedelta(minutes=1)
    # --- 修复逻辑结束 ---

    time_range = st.slider(
        "时间范围", 
        min_value=min_t, 
        max_value=max_t, 
        value=(min_t, max_t),
        format="MM/DD HH:mm" # 优化显示格式
    )
# 数据过滤
filtered_df = df_all[
    (df_all['Variety'].isin(selected_varieties)) &
    (df_all['Time'] >= time_range[0]) &
    (df_all['Time'] <= time_range[1])
]

# --- 图表展示 ---
st.header('价格走势图', divider='orange')

if not filtered_df.empty:
    # 绘图
    st.line_chart(
        filtered_df,
        x='Time',
        y='Price',
        color='Variety',
    )
    
    # --- 关键指标 (Metrics) ---
    st.header('当前各品种详情', divider='gray')
    cols = st.columns(len(selected_varieties))
    
    for i, var in enumerate(selected_varieties):
        var_data = filtered_df[filtered_df['Variety'] == var]
        if not var_data.empty:
            current_p = var_data['Price'].iloc[-1]
            # 计算对比范围内的涨跌
            start_p = var_data['Price'].iloc[0]
            delta = f"{current_p - start_p:.2f}"
            
            with cols[i % len(cols)]:
                st.metric(label=var, value=f"¥{current_p}", delta=delta)
else:
    st.warning("请在侧边栏至少选择一个品种进行展示。")

# --- 数据导出 ---
if st.checkbox("查看底层数据"):
    st.dataframe(filtered_df.sort_values('Time', ascending=False), use_container_width=True)