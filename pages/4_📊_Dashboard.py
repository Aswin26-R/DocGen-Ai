import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd
from collections import defaultdict
from backend.auth import check_authentication, render_logout_button
from backend.utils import initialize_session_state

# Page configuration
st.set_page_config(
    page_title="Dashboard - DocGen",
    page_icon="📊",
    layout="wide"
)

# Authentication check
if not check_authentication():
    st.error("Please log in from the main page first.")
    st.stop()

# Initialize session state
initialize_session_state()

# Render logout button
render_logout_button()

st.title("📊 Learning Dashboard")
st.markdown("Track your learning progress and performance metrics.")

# Helper functions
def get_date_from_iso(iso_string):
    """Convert ISO string to date"""
    try:
        return datetime.fromisoformat(iso_string.replace('Z', '+00:00')).date()
    except:
        return datetime.now().date()

def calculate_performance_metrics():
    """Calculate performance metrics from quiz history"""
    if not st.session_state.quiz_history:
        return {}
    
    metrics = {
        'total_quizzes': len(st.session_state.quiz_history),
        'average_score': sum(q.get('score', 0) for q in st.session_state.quiz_history) / len(st.session_state.quiz_history),
        'best_score': max(q.get('score', 0) for q in st.session_state.quiz_history),
        'recent_score': st.session_state.quiz_history[-1].get('score', 0) if st.session_state.quiz_history else 0
    }
    
    # Quiz type breakdown
    type_counts = defaultdict(int)
    type_scores = defaultdict(list)
    
    for quiz in st.session_state.quiz_history:
        quiz_type = quiz.get('type', 'unknown')
        type_counts[quiz_type] += 1
        type_scores[quiz_type].append(quiz.get('score', 0))
    
    metrics['type_breakdown'] = dict(type_counts)
    metrics['type_averages'] = {k: sum(v) / len(v) for k, v in type_scores.items()}
    
    return metrics

def generate_activity_calendar():
    """Generate activity calendar data"""
    activity_data = defaultdict(int)
    
    # Count activities by date
    for activity in st.session_state.activity_log:
        try:
            date = datetime.fromisoformat(activity['timestamp'].replace('Z', '+00:00')).date()
            activity_data[date] += 1
        except:
            continue
    
    # Generate last 90 days
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=89)
    
    dates = []
    activities = []
    
    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date)
        activities.append(activity_data.get(current_date, 0))
        current_date += timedelta(days=1)
    
    return dates, activities

# Main dashboard content
if not st.session_state.quiz_history and not st.session_state.documents:
    st.info("Welcome to your dashboard! Start by uploading documents and taking quizzes to see your progress here.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📚 Upload Documents", use_container_width=True):
            st.switch_page("pages/1_📚_Document_Library.py")
    with col2:
        if st.button("🧠 Take Quiz", use_container_width=True):
            st.switch_page("pages/2_🧠_Quiz_Center.py")
    st.stop()

# Key metrics row
st.subheader("📈 Key Metrics")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="📄 Documents",
        value=len(st.session_state.documents),
        help="Total documents in your library"
    )

with col2:
    total_quizzes = len(st.session_state.quiz_history)
    st.metric(
        label="🎯 Quizzes Taken",
        value=total_quizzes,
        help="Total number of quizzes completed"
    )

with col3:
    st.metric(
        label="📝 Summaries",
        value=len(st.session_state.summaries),
        help="Total summaries generated"
    )

with col4:
    avg_score = 0
    if st.session_state.quiz_history:
        scores = [q.get('score', 0) for q in st.session_state.quiz_history]
        avg_score = sum(scores) / len(scores)
    
    # Calculate delta from previous average
    delta = None
    if len(st.session_state.quiz_history) >= 2:
        recent_scores = scores[-3:] if len(scores) >= 3 else scores[-2:]
        prev_scores = scores[:-len(recent_scores)]
        if prev_scores:
            prev_avg = sum(prev_scores) / len(prev_scores)
            recent_avg = sum(recent_scores) / len(recent_scores)
            delta = f"{recent_avg - prev_avg:.1f}%"
    
    st.metric(
        label="📊 Avg Score",
        value=f"{avg_score:.1f}%",
        delta=delta,
        help="Average quiz score across all attempts"
    )

# Performance analysis
if st.session_state.quiz_history:
    metrics = calculate_performance_metrics()
    
    st.markdown("---")
    st.subheader("🎯 Performance Analysis")
    
    # Score trend chart
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("**📈 Score Trend Over Time**")
        
        # Prepare data for trend chart
        quiz_dates = []
        quiz_scores = []
        quiz_types = []
        
        for i, quiz in enumerate(st.session_state.quiz_history):
            quiz_dates.append(i + 1)  # Use quiz number as x-axis
            quiz_scores.append(quiz.get('score', 0))
            quiz_types.append(quiz.get('type', 'unknown').replace('_', ' ').title())
        
        # Create trend chart
        fig = px.line(
            x=quiz_dates,
            y=quiz_scores,
            title="Quiz Score Progression",
            labels={'x': 'Quiz Number', 'y': 'Score (%)'},
            markers=True
        )
        
        # Add target line at 80%
        fig.add_hline(y=80, line_dash="dash", line_color="green", 
                     annotation_text="Target: 80%")
        
        fig.update_layout(
            showlegend=False,
            height=300,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("**🏆 Performance Highlights**")
        
        st.metric("Best Score", f"{metrics['best_score']:.1f}%")
        st.metric("Recent Score", f"{metrics['recent_score']:.1f}%")
        
        # Progress towards goals
        if avg_score >= 90:
            st.success("🌟 Excellent Performance!")
        elif avg_score >= 80:
            st.success("✅ Great Job!")
        elif avg_score >= 70:
            st.info("👍 Good Progress!")
        else:
            st.warning("📚 Keep Studying!")
    
    # Quiz type analysis
    st.markdown("**📊 Quiz Type Performance**")
    
    if len(metrics['type_breakdown']) > 1:
        col1, col2 = st.columns(2)
        
        with col1:
            # Quiz type distribution
            fig_pie = px.pie(
                values=list(metrics['type_breakdown'].values()),
                names=[t.replace('_', ' ').title() for t in metrics['type_breakdown'].keys()],
                title="Quiz Type Distribution"
            )
            fig_pie.update_layout(height=300, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Average scores by type
            fig_bar = px.bar(
                x=[t.replace('_', ' ').title() for t in metrics['type_averages'].keys()],
                y=list(metrics['type_averages'].values()),
                title="Average Score by Quiz Type",
                labels={'x': 'Quiz Type', 'y': 'Average Score (%)'}
            )
            fig_bar.update_layout(height=300, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_bar, use_container_width=True)
    else:
        # Single type display
        quiz_type = list(metrics['type_breakdown'].keys())[0]
        avg_score_type = metrics['type_averages'][quiz_type]
        
        st.info(f"**{quiz_type.replace('_', ' ').title()}**: {metrics['type_breakdown'][quiz_type]} quizzes, {avg_score_type:.1f}% average")

# Activity calendar
st.markdown("---")
st.subheader("📅 Activity Calendar")

if st.session_state.activity_log:
    dates, activities = generate_activity_calendar()
    
    # Create calendar heatmap
    df_calendar = pd.DataFrame({
        'Date': dates,
        'Activities': activities,
        'Day': [d.strftime('%A') for d in dates],
        'Week': [(d - dates[0]).days // 7 for d in dates]
    })
    
    # Pivot for heatmap
    calendar_pivot = df_calendar.pivot_table(
        index='Day',
        columns='Week',
        values='Activities',
        fill_value=0
    )
    
    # Reorder days
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    calendar_pivot = calendar_pivot.reindex(day_order)
    
    fig_heatmap = px.imshow(
        calendar_pivot,
        labels=dict(x="Week", y="Day", color="Activities"),
        title="Activity Heatmap (Last 90 Days)",
        color_continuous_scale="Greens"
    )
    
    fig_heatmap.update_layout(
        height=300,
        xaxis_title="Week",
        yaxis_title="",
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    st.plotly_chart(fig_heatmap, use_container_width=True)
    
    # Activity summary
    total_active_days = sum(1 for a in activities if a > 0)
    current_streak = 0
    
    # Calculate current streak
    for activity in reversed(activities):
        if activity > 0:
            current_streak += 1
        else:
            break
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🔥 Current Streak", f"{current_streak} days")
    with col2:
        st.metric("📊 Active Days", f"{total_active_days}/90")
    with col3:
        activity_rate = (total_active_days / 90) * 100
        st.metric("📈 Activity Rate", f"{activity_rate:.1f}%")

else:
    st.info("No activity data available yet. Start using the app to see your activity calendar!")

# Recent activity feed
st.markdown("---")
st.subheader("🕒 Recent Activity")

if st.session_state.activity_log:
    # Show last 10 activities
    recent_activities = st.session_state.activity_log[-10:]
    
    for activity in reversed(recent_activities):
        timestamp = activity['timestamp']
        action = activity['action']
        
        # Format timestamp
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            time_str = dt.strftime('%m/%d %H:%M')
        except:
            time_str = timestamp
        
        st.info(f"**{time_str}** - {action}")

else:
    st.info("No recent activity. Start by uploading documents or taking quizzes!")

# Learning insights
st.markdown("---")
st.subheader("💡 Learning Insights")

insights = []

if st.session_state.quiz_history:
    # Performance insights
    if avg_score >= 85:
        insights.append("🌟 Excellent work! Your average score shows strong understanding.")
    elif avg_score >= 75:
        insights.append("👍 Good performance! Consider challenging yourself with harder material.")
    else:
        insights.append("📚 Focus on reviewing material before taking quizzes to improve scores.")
    
    # Activity insights
    if len(st.session_state.quiz_history) >= 5:
        recent_scores = [q.get('score', 0) for q in st.session_state.quiz_history[-5:]]
        if all(score >= 80 for score in recent_scores):
            insights.append("🔥 Great consistency! Your recent scores are all above 80%.")
    
    # Content insights
    if len(st.session_state.documents) > len(st.session_state.quiz_history):
        insights.append("📖 You have more documents than completed quizzes. Try creating quizzes from more of your materials.")

# Document insights
if st.session_state.documents:
    doc_types = [doc.get('source', 'unknown') for doc in st.session_state.documents]
    if 'arxiv' in doc_types and 'upload' in doc_types:
        insights.append("🔬 Great mix of academic papers and personal documents!")

# Summary insights
if len(st.session_state.summaries) > 0:
    summary_ratio = len(st.session_state.summaries) / len(st.session_state.documents) if st.session_state.documents else 0
    if summary_ratio >= 0.5:
        insights.append("📝 Excellent! You're creating summaries for most of your documents.")

if insights:
    for insight in insights:
        st.success(insight)
else:
    st.info("Keep using DocGen to unlock personalized learning insights!")

# Goals section
with st.sidebar:
    st.subheader("🎯 Learning Goals")
    
    # Weekly goal
    weekly_target = st.number_input("Weekly Quiz Target", min_value=1, max_value=20, value=3)
    
    # Calculate this week's progress
    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())
    
    this_week_quizzes = sum(
        1 for quiz in st.session_state.quiz_history
        if get_date_from_iso(quiz.get('completed_at', '')) >= week_start
    )
    
    st.progress(min(this_week_quizzes / weekly_target, 1.0))
    st.caption(f"This week: {this_week_quizzes}/{weekly_target} quizzes")
    
    # Score goal
    score_target = st.slider("Target Average Score", 60, 100, 80)
    
    if st.session_state.quiz_history:
        score_progress = min(avg_score / score_target, 1.0)
        st.progress(score_progress)
        st.caption(f"Current: {avg_score:.1f}% / {score_target}%")
