# app.py - requests를 사용하는 이력서 맞춤화 Streamlit 앱
import streamlit as st
import json
import os
import requests
import time

# 페이지 설정
st.set_page_config(
    page_title="이력서 맞춤화 시스템",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 스타일 추가
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1rem;
    }
    .section-header {
        font-size: 1.8rem;
        color: #0D47A1;
        border-bottom: 2px solid #BBDEFB;
        padding-bottom: 0.5rem;
        margin-top: 2rem;
    }
    .subsection-header {
        font-size: 1.3rem;
        color: #1565C0;
        margin-top: 1.5rem;
    }
    .result-area {
        background-color: #F5F5F5;
        padding: 1rem;
        border-radius: 5px;
        border-left: 5px solid #1E88E5;
    }
    .success-message {
        padding: 1rem;
        background-color: #E8F5E9;
        border-radius: 5px;
        border-left: 5px solid #43A047;
    }
    .info-message {
        padding: 1rem;
        background-color: #E3F2FD;
        border-radius: 5px;
        border-left: 5px solid #1E88E5;
    }
</style>
""", unsafe_allow_html=True)

# 앱 제목
st.markdown("<h1 class='main-header'>이력서 자동 맞춤화 시스템</h1>", unsafe_allow_html=True)

# 초기 상태 설정
if 'resume_versions' not in st.session_state:
    st.session_state.resume_versions = {}
if 'job_postings' not in st.session_state:
    st.session_state.job_postings = {}
if 'job_analyses' not in st.session_state:
    st.session_state.job_analyses = {}
if 'customization_settings' not in st.session_state:
    st.session_state.customization_settings = {}
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""
if 'selected_model' not in st.session_state:
    st.session_state.selected_model = "claude-3-5-sonnet-20240620"
if 'resume_sections' not in st.session_state:
    st.session_state.resume_sections = None
if 'tailored_result' not in st.session_state:
    st.session_state.tailored_result = None

#Anthropic API 호출 함수
def call_anthropic_api(prompt, model="claude-3-haiku-20240307", max_tokens=4000, temperature=0.3, system=""):
    api_key = st.session_state.api_key
    
    if not api_key:
        raise Exception("API 키가 설정되지 않았습니다.")
    
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    data = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    if system:
        data["system"] = system
    
    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=data
        )
        
        if response.status_code != 200:
            raise Exception(f"API 오류: {response.status_code} - {response.text}")
        
        return response.json()["content"][0]["text"]
    except Exception as e:
        raise Exception(f"API 호출 오류: {str(e)}")

# 채용 공고 분석 함수
def analyze_job_posting(job_id):
    """채용 공고를 분석하여 주요 요구사항, 키워드, 우대사항 등을 추출"""
    job_content = st.session_state.job_postings[job_id]['content']
    
    try:
        # 프롬프트 구성
        prompt = f"""
        당신은 채용 공고 분석 전문가입니다. 다음 채용 공고를 분석하여 구직자가 이력서를 최적화하는 데 필요한 정보를 추출해주세요.
        
        ## 채용 공고:
        {job_content}
        
        다음 형식으로 분석 결과를 제공해주세요:
        
        1. 직무 요약: [직무에 대한 간략한 요약]
        2. 핵심 요구사항: [필수적인 기술, 경험, 자격 요건을 항목별로 나열]
        3. 우대사항: [우대하는 기술, 경험, 자격 요건을 항목별로 나열]
        4. 주요 키워드: [이력서에 포함되면 좋을 핵심 키워드 10-15개 나열]
        5. 회사 가치관/문화: [회사가 중요시하는 가치나 문화적 특성]
        6. 이력서 최적화 전략: [이 채용 공고에 맞게 이력서를 최적화하는 구체적인 전략과 조언]
        
        각 섹션을 상세하게 작성해주시고, 채용 공고에서 명시적으로 언급되지 않았지만 해당 직무에서 중요할 수 있는 요소도 포함해주세요.
        """
        
        # API 호출
        analysis_result = call_anthropic_api(
            prompt=prompt,
            model=st.session_state.selected_model,
            max_tokens=4000,
            temperature=0.3,
            system="당신은 채용 공고 분석 전문가입니다. 구직자가 이력서를 최적화할 수 있도록 채용 공고의 핵심 내용을 분석해주세요."
        )
        
        # 분석 결과 저장
        st.session_state.job_analyses[job_id] = analysis_result
        
        return analysis_result
        
    except Exception as e:
        raise Exception(f"채용 공고 분석 중 오류 발생: {str(e)}")

# 고급 이력서 맞춤화 함수
def tailor_resume_advanced(job_id, selected_resume_names):
    """채용 공고, 분석 결과, 맞춤화 설정을 적용하여 이력서 최적화"""
    job_content = st.session_state.job_postings[job_id]['content']
    job_title = st.session_state.job_postings[job_id]['title']
    
    # 선택된 이력서 내용 가져오기
    selected_contents = [st.session_state.resume_versions[name] for name in selected_resume_names]
    
    # 맞춤화 설정 가져오기
    custom_settings = st.session_state.customization_settings.get(job_id, {})
    emphasis = custom_settings.get('emphasis_skills', '')
    deemphasis = custom_settings.get('deemphasize_skills', '')
    
    tone_map = {
        'professional': '전문적/공식적',
        'creative': '창의적/활기찬',
        'balanced': '균형잡힌/중립적',
        'results_driven': '성과 중심적',
        'collaborative': '협업 중심적'
    }
    
    tone = tone_map.get(custom_settings.get('tone', 'professional'), '전문적/공식적')
    length_val = custom_settings.get('length', 2)
    length_desc = ['간결한', '표준', '상세한'][length_val-1]
    
    # 분석 결과 가져오기
    analysis = st.session_state.job_analyses.get(job_id, '아직 분석되지 않았습니다.')
    
    try:
        # 프롬프트 구성
        prompt = f"""
        당신은 전문 이력서 맞춤화 전문가입니다. 다음 이력서 버전들을 참고하여 
        제공된 채용 공고에 최적화된 새로운 이력서를 작성해 주세요.
        
        ## 채용 공고: {job_title}
        {job_content}
        
        ## 채용 공고 분석 결과:
        {analysis}
        
        ## 이력서 버전들:
        {selected_contents}
        
        ## 맞춤화 설정:
        - 강조할 기술/경험: {emphasis}
        - 약화할 기술/경험: {deemphasis}
        - 이력서 톤: {tone}
        - 이력서 길이: {length_desc}
        
        다음 지침에 따라 이력서를 맞춤화해주세요:
        1. 채용 공고의 요구사항과 일치하는 기술, 경험, 성과를 강조하세요.
        2. 관련성이 낮은 내용은 줄이거나 제외하세요.
        3. 위에서 지정한 '강조할 기술/경험'을 특별히 부각시키세요.
        4. '약화할 기술/경험'은 최소화하거나 더 관련성 있는 다른 기술로 대체하세요.
        5. 지정된 톤({tone})에 맞게 문체를 조정하세요.
        6. 이력서 길이는 {length_desc} 수준으로 조정하세요.
        7. 이력서 형식과 구조는 원본 이력서를 따라주세요.
        8. 채용 공고 분석 결과의 주요 키워드와 핵심 요구사항을 반영하세요.
        
        최종 이력서는 구직자가 이 특정 채용 공고에 가장 적합한 후보자로 보이도록 맞춤화되어야 합니다.
        """
        
        # API 호출
        result = call_anthropic_api(
            prompt=prompt,
            model=st.session_state.selected_model,
            max_tokens=4000,
            temperature=0.3,
            system="당신은 전문 이력서 맞춤화 전문가입니다. 채용 공고에 가장 적합한 이력서를 작성해 주세요."
        )
        
        # 결과 반환
        return result
    
    except Exception as e:
        raise Exception(f"이력서 맞춤화 중 오류 발생: {str(e)}")
2. 필요한 코드 변경사항
다음은 app.py 파일에 추가할 코드의 핵심 부분입니다:
python# 이력서 섹션 분리 함수 추가
def split_resume_sections(resume_text):
    """이력서를 섹션별로 분리"""
    try:
        sections = call_anthropic_api(
            prompt=f"""
            다음 이력서를 주요 섹션으로 분리해주세요:
            
            {resume_text}
            
            다음 형식으로 분리된 섹션들을 JSON 형식으로 반환해주세요:
            {{
              "professional_summary": "전문 요약 내용...",
              "work_experience": [
                {{"title": "직위1", "company": "회사1", "content": "상세 내용..."}},
                {{"title": "직위2", "company": "회사2", "content": "상세 내용..."}}
              ],
              "education": [
                {{"degree": "학위1", "institution": "학교1", "content": "상세 내용..."}},
                {{"degree": "학위2", "institution": "학교2", "content": "상세 내용..."}}
              ],
              "skills": ["기술1", "기술2", "기술3"],
              "projects": [
                {{"name": "프로젝트1", "content": "상세 내용..."}},
                {{"name": "프로젝트2", "content": "상세 내용..."}}
              ],
              "additional_sections": [
                {{"title": "섹션 제목1", "content": "상세 내용..."}},
                {{"title": "섹션 제목2", "content": "상세 내용..."}}
              ]
            }}
            
            JSON 형식만 출력해주세요.
            """,
            model=st.session_state.selected_model,
            temperature=0.0
        )
        
        # JSON 문자열에서 실제 JSON 객체로 변환
        import json
        cleaned_json = sections.strip('```json').strip('```').strip()
        return json.loads(cleaned_json)
    except Exception as e:
        st.error(f"이력서 섹션 분리 중 오류 발생: {str(e)}")
        return None

# 섹션별 수정 함수 추가
def update_resume_section(section_type, section_content, feedback, job_description, job_analysis):
    """사용자 피드백에 따라 특정 섹션만 수정"""
    try:
        updated_section = call_anthropic_api(
            prompt=f"""
            다음은 이력서의 '{section_type}' 섹션입니다:
            
            {section_content}
            
            사용자가 이 섹션에 대해 다음과 같은 피드백을 제공했습니다:
            
            {feedback}
            
            관련 채용 공고:
            {job_description}
            
            채용 공고 분석:
            {job_analysis}
            
            사용자의 피드백을 반영하여 이 섹션을 다시 작성해주세요. 
            원래 섹션의 핵심 정보는 유지하되, 피드백에 따라 내용, 표현, 강조점을 조정해주세요.
            피드백에 언급된 사항만 수정하고, 그 외 부분은 가능한 유지해주세요.
            """,
            model=st.session_state.selected_model,
            temperature=0.3
        )
        
        return updated_section
    except Exception as e:
        st.error(f"섹션 수정 중 오류 발생: {str(e)}")
        return None

# 사이드바에 API 키 설정
with st.sidebar:
    st.header("🔑 API 설정")
    api_key = st.text_input("Anthropic API 키", type="password", value=st.session_state.api_key)
    
    if api_key:
        if api_key != st.session_state.api_key:
            st.session_state.api_key = api_key
            st.success("API 키가 설정되었습니다!")
    
    # 모델 선택
    st.header("🤖 AI 모델 설정")
    models = {
        "Claude 3.7 Sonnet (최신)": "claude-3-7-sonnet-20250219",
        "Claude 3.5 Sonnet": "claude-3-5-sonnet-20240620",
        "Claude 3 Opus": "claude-3-opus-20240229",
        "Claude 3 Haiku": "claude-3-haiku-20240307"
    }
    selected_model = st.selectbox("AI 모델 선택", list(models.keys()))
    st.session_state.selected_model = models[selected_model]
    
    # 데이터 저장 및 불러오기
    st.header("💾 데이터 관리")
    
    # 데이터 저장
    if st.button("모든 데이터 저장"):
        data = {
            "resume_versions": st.session_state.resume_versions,
            "job_postings": st.session_state.job_postings,
            "job_analyses": st.session_state.job_analyses,
            "customization_settings": st.session_state.customization_settings
        }
        
        # JSON으로 변환
        json_data = json.dumps(data, ensure_ascii=False, indent=2)
        
        # 다운로드 버튼 표시
        st.download_button(
            label="JSON 파일 다운로드",
            data=json_data,
            file_name="resume_system_data.json",
            mime="application/json"
        )
    
    # 데이터 불러오기
    uploaded_file = st.file_uploader("데이터 파일 업로드", type="json")
    if uploaded_file:
        try:
            data = json.load(uploaded_file)
            st.session_state.resume_versions = data.get("resume_versions", {})
            st.session_state.job_postings = data.get("job_postings", {})
            st.session_state.job_analyses = data.get("job_analyses", {})
            st.session_state.customization_settings = data.get("customization_settings", {})
            st.success(f"데이터를 성공적으로 불러왔습니다!")
        except Exception as e:
            st.error(f"데이터 불러오기 오류: {e}")

# 탭 생성
tabs = st.tabs(["이력서 관리", "채용 공고 관리", "채용 공고 분석", "이력서 맞춤화"])

# 1. 이력서 관리 탭
with tabs[0]:
    st.markdown("<h2 class='section-header'>이력서 버전 관리</h2>", unsafe_allow_html=True)
    
    # 이력서 추가 폼
    with st.expander("새 이력서 추가", expanded=True):
        col1, col2 = st.columns([1, 1])
        with col1:
            version_name = st.text_input("이력서 버전 이름", placeholder="예: 개발자용, 기획자용, 일반 버전")
        
        resume_content = st.text_area("이력서 내용", height=300, placeholder="이력서 내용을 여기에 붙여넣으세요...")
        
        if st.button("이력서 저장", use_container_width=True):
            if version_name and resume_content:
                st.session_state.resume_versions[version_name] = resume_content
                st.success(f"'{version_name}' 이력서가 저장되었습니다!")
                # 입력 필드 초기화를 위한 rerun
                st.experimental_rerun()
            else:
                st.error("이력서 이름과 내용을 모두 입력해주세요.")
    
    # 저장된 이력서 목록
    st.markdown("<h3 class='subsection-header'>저장된 이력서 목록</h3>", unsafe_allow_html=True)
    
    if not st.session_state.resume_versions:
        st.info("저장된 이력서가 없습니다. 위에서 이력서를 추가해보세요.")
    else:
        for version, content in st.session_state.resume_versions.items():
            with st.expander(f"📄 {version}"):
                st.text_area("내용", value=content, height=200, key=f"resume_{version}", disabled=True)
                col1, col2 = st.columns([1, 5])
                with col1:
                    if st.button("삭제", key=f"delete_{version}"):
                        del st.session_state.resume_versions[version]
                        st.success(f"'{version}' 이력서가 삭제되었습니다.")
                        st.experimental_rerun()

# 2. 채용 공고 관리 탭
with tabs[1]:
    st.markdown("<h2 class='section-header'>채용 공고 관리</h2>", unsafe_allow_html=True)
    
    # 채용 공고 추가 폼
    with st.expander("새 채용 공고 추가", expanded=True):
        col1, col2 = st.columns([1, 1])
        with col1:
            job_title = st.text_input("채용 공고 제목", placeholder="예: 프론트엔드 개발자, 마케팅 매니저")
        
        job_content = st.text_area("채용 공고 내용", height=300, placeholder="채용 공고의 전체 내용을 여기에 붙여넣으세요...")
        
        if st.button("채용 공고 저장", use_container_width=True):
            if job_title and job_content:
                # 채용 공고 ID 생성
                job_id = f"{job_title.replace(' ', '_')}_{int(time.time())}"
                
                # 채용 공고 저장
                st.session_state.job_postings[job_id] = {
                    'title': job_title,
                    'content': job_content
                }
                
                st.success(f"'{job_title}' 채용 공고가 저장되었습니다!")
                # 입력 필드 초기화를 위한 rerun
                st.experimental_rerun()
            else:
                st.error("채용 공고 제목과 내용을 모두 입력해주세요.")
    
    # 저장된 채용 공고 목록
    st.markdown("<h3 class='subsection-header'>저장된 채용 공고 목록</h3>", unsafe_allow_html=True)
    
    if not st.session_state.job_postings:
        st.info("저장된 채용 공고가 없습니다. 위에서 채용 공고를 추가해보세요.")
    else:
        for job_id, job_data in st.session_state.job_postings.items():
            with st.expander(f"📄 {job_data['title']}"):
                st.text_area("내용", value=job_data['content'], height=200, key=f"job_{job_id}", disabled=True)
                col1, col2 = st.columns([1, 5])
                with col1:
                    if st.button("삭제", key=f"delete_job_{job_id}"):
                        del st.session_state.job_postings[job_id]
                        if job_id in st.session_state.job_analyses:
                            del st.session_state.job_analyses[job_id]
                        if job_id in st.session_state.customization_settings:
                            del st.session_state.customization_settings[job_id]
                        st.success(f"'{job_data['title']}' 채용 공고가 삭제되었습니다.")
                        st.experimental_rerun()

# 3. 채용 공고 분석 탭
with tabs[2]:
    st.markdown("<h2 class='section-header'>채용 공고 분석</h2>", unsafe_allow_html=True)
    
    # API 키 확인
    if not st.session_state.api_key:
        st.warning("사이드바에서 Anthropic API 키를 먼저 설정해주세요.")
    
    # 채용 공고 선택
    if not st.session_state.job_postings:
        st.info("저장된 채용 공고가 없습니다. '채용 공고 관리' 탭에서 채용 공고를 추가해주세요.")
    else:
        job_options = {job_data['title']: job_id for job_id, job_data in st.session_state.job_postings.items()}
        selected_job_title = st.selectbox("분석할 채용 공고 선택", options=list(job_options.keys()))
        selected_job_id = job_options[selected_job_title]
        
        # 이미 분석된 경우 결과 표시
        if selected_job_id in st.session_state.job_analyses:
            st.markdown("<div class='info-message'>이 채용 공고는 이미 분석되었습니다. 다시 분석하려면 아래 버튼을 클릭하세요.</div>", unsafe_allow_html=True)
            if st.button("다시 분석", use_container_width=True):
                with st.spinner("채용 공고를 분석하는 중..."):
                    try:
                        analysis_result = analyze_job_posting(selected_job_id)
                        st.success("채용 공고 분석이 완료되었습니다!")
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"분석 중 오류가 발생했습니다: {str(e)}")
            
            st.markdown("<h3 class='subsection-header'>분석 결과</h3>", unsafe_allow_html=True)
            st.markdown("<div class='result-area'>" + st.session_state.job_analyses[selected_job_id].replace('\n', '<br>') + "</div>", unsafe_allow_html=True)
            
        else:
            st.info("이 채용 공고는 아직 분석되지 않았습니다.")
            
            if st.button("채용 공고 분석", use_container_width=True):
                with st.spinner("채용 공고를 분석하는 중..."):
                    try:
                        analysis_result = analyze_job_posting(selected_job_id)
                        st.success("채용 공고 분석이 완료되었습니다!")
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"분석 중 오류가 발생했습니다: {str(e)}")

# 4. 이력서 맞춤화 탭
with tabs[3]:
    st.markdown("<h2 class='section-header'>이력서 맞춤화</h2>", unsafe_allow_html=True)
    
    # API 키 확인
    if not st.session_state.api_key:
        st.warning("사이드바에서 Anthropic API 키를 먼저 설정해주세요.")
    
    # 이력서 및 채용 공고 여부 확인
    if not st.session_state.resume_versions:
        st.warning("저장된 이력서가 없습니다. '이력서 관리' 탭에서 이력서를 추가해주세요.")
    
    if not st.session_state.job_postings:
        st.warning("저장된 채용 공고가 없습니다. '채용 공고 관리' 탭에서 채용 공고를 추가해주세요.")
    
    if st.session_state.resume_versions and st.session_state.job_postings:
        # 채용 공고 선택
        job_options = {job_data['title']: job_id for job_id, job_data in st.session_state.job_postings.items()}
        selected_job_title = st.selectbox("맞춤화할 채용 공고 선택", options=list(job_options.keys()), key="customize_job")
        selected_job_id = job_options[selected_job_title]
        
        # 분석 결과 확인 및 분석 권장
        if selected_job_id not in st.session_state.job_analyses:
            st.info("이 채용 공고는 아직 분석되지 않았습니다. '채용 공고 분석' 탭에서 먼저 분석하는 것을 권장합니다.")
        
        # 이력서 버전 선택
        st.markdown("<h3 class='subsection-header'>사용할 이력서 버전 선택</h3>", unsafe_allow_html=True)
        resume_options = list(st.session_state.resume_versions.keys())
        selected_resumes = st.multiselect("이력서 버전", options=resume_options)
        
        # 맞춤화 설정
        st.markdown("<h3 class='subsection-header'>맞춤화 설정</h3>", unsafe_allow_html=True)
        
        # 기존 설정 가져오기
        current_settings = st.session_state.customization_settings.get(selected_job_id, {})
        
        col1, col2 = st.columns(2)
        with col1:
            emphasis_skills = st.text_area(
                "강조할 기술/경험",
                placeholder="예: Python, 리더십, 프로젝트 관리 경험",
                height=100,
                value=current_settings.get('emphasis_skills', '')
            )
        
        with col2:
            deemphasize_skills = st.text_area(
                "약화할 기술/경험",
                placeholder="예: Java, 영업 경험, 해외 근무",
                height=100,
                value=current_settings.get('deemphasis_skills', '')
            )
        
        col3, col4 = st.columns(2)
        with col3:
            tone_options = [
                '전문적/공식적',
                '창의적/활기찬',
                '균형잡힌/중립적',
                '성과 중심적',
                '협업 중심적'
            ]
            tone_values = [
                'professional',
                'creative',
                'balanced',
                'results_driven',
                'collaborative'
            ]
            
            selected_tone_index = tone_values.index(current_settings.get('tone', 'professional')) if current_settings.get('tone', 'professional') in tone_values else 0
            selected_tone = st.selectbox("이력서 톤", options=tone_options, index=selected_tone_index)
            tone_value = tone_values[tone_options.index(selected_tone)]
        
        with col4:
            length_value = current_settings.get('length', 2)
            length = st.slider("이력서 길이", min_value=1, max_value=3, value=length_value, 
                             help="1: 간결함, 2: 표준, 3: 상세함")
        
        # 맞춤화 설정 저장
        if st.button("맞춤화 설정 저장", use_container_width=True):
            st.session_state.customization_settings[selected_job_id] = {
                'emphasis_skills': emphasis_skills,
                'deemphasize_skills': deemphasize_skills,
                'tone': tone_value,
                'length': length
            }
            st.success("맞춤화 설정이 저장되었습니다!")
        
        # 이력서 맞춤화 실행
        if st.button("이력서 맞춤화 시작", use_container_width=True, type="primary"):
            if not selected_resumes:
                st.error("최소한 하나의 이력서 버전을 선택해주세요.")
            else:
                with st.spinner("이력서를 맞춤화하는 중... 잠시만 기다려주세요."):
                    try:
                        st.session_state.tailored_result = tailor_resume_advanced(selected_job_id, selected_resumes)
                        result = st.session_state.tailored_result
                        
                        st.markdown("<h3 class='subsection-header'>맞춤화된 이력서 결과</h3>", unsafe_allow_html=True)
                        st.markdown("<div class='result-area'>" + result.replace('\n', '<br>') + "</div>", unsafe_allow_html=True)
                        
                        # 결과 다운로드
                        st.download_button(
                            label="결과 다운로드",
                            data=result,
                            file_name=f"맞춤화된_이력서_{selected_job_title.replace(' ', '_')}.txt",
                            mime="text/plain"
                        )
                        
                        # 새 버전으로 저장
                        new_version_name = st.text_input("새 이력서 버전 이름", value=f"맞춤화된 이력서 - {selected_job_title}")
                        if st.button("새 버전으로 저장"):
                            if new_version_name:
                                st.session_state.resume_versions[new_version_name] = result
                                st.success(f"'{new_version_name}' 이름으로 새 이력서가 저장되었습니다!")
                            else:
                                st.error("이력서 버전 이름을 입력해주세요.")
                    except Exception as e:
                        st.error(f"맞춤화 중 오류가 발생했습니다: {str(e)}")
# 섹션별 피드백 및 수정 UI 코드 추가
if 'tailored_result' in st.session_state and st.session_state.tailored_result:
    st.markdown("<h3 class='subsection-header'>섹션별 피드백 및 수정</h3>", unsafe_allow_html=True)
    
    if 'resume_sections' not in st.session_state or not st.session_state.resume_sections:
        if st.button("이력서 섹션 분리하기"):
            with st.spinner("이력서를 섹션별로 분리하는 중..."):
                st.session_state.resume_sections = split_resume_sections(st.session_state.tailored_result)
    
    if 'resume_sections' in st.session_state and st.session_state.resume_sections:
        # 전문 요약 섹션 수정
        with st.expander("전문 요약 수정", expanded=False):
            summary = st.session_state.resume_sections.get("professional_summary", "")
            st.text_area("현재 전문 요약", value=summary, height=100, disabled=True)
            summary_feedback = st.text_area("수정 요청 사항", 
                placeholder="예: 리더십 역량을 더 강조해주세요. AI 관련 경험을 추가해주세요.")
            if st.button("전문 요약 업데이트"):
                with st.spinner("전문 요약을 수정하는 중..."):
                    updated_summary = update_resume_section(
                        "전문 요약", 
                        summary,
                        summary_feedback,
                        st.session_state.job_postings[selected_job_id]['content'],
                        st.session_state.job_analyses.get(selected_job_id, "")
                    )
                    if updated_summary:
                        st.session_state.resume_sections["professional_summary"] = updated_summary
                        st.success("전문 요약이 업데이트되었습니다!")
                        st.text_area("수정된 전문 요약", value=updated_summary, height=150)
        
        # 직무 경험 섹션 수정
        with st.expander("직무 경험 수정", expanded=False):
            work_experiences = st.session_state.resume_sections.get("work_experience", [])
            for i, exp in enumerate(work_experiences):
                st.subheader(f"{exp.get('title')} at {exp.get('company')}")
                st.text_area(f"현재 내용 #{i+1}", value=exp.get('content', ""), height=100, disabled=True, key=f"exp_{i}")
                exp_feedback = st.text_area("수정 요청 사항", 
                    placeholder="예: 성과를 수치로 더 자세히 표현해주세요.",
                    key=f"exp_feedback_{i}")
                if st.button(f"이 경험 업데이트", key=f"update_exp_{i}"):
                    with st.spinner("직무 경험을 수정하는 중..."):
                        updated_exp = update_resume_section(
                            "직무 경험", 
                            exp.get('content', ""),
                            exp_feedback,
                            st.session_state.job_postings[selected_job_id]['content'],
                            st.session_state.job_analyses.get(selected_job_id, "")
                        )
                        if updated_exp:
                            st.session_state.resume_sections["work_experience"][i]["content"] = updated_exp
                            st.success("직무 경험이 업데이트되었습니다!")
                            st.text_area(f"수정된 내용", value=updated_exp, height=150)
                st.divider()
        
        # 최종 이력서 재구성 버튼
        if st.button("업데이트된 섹션으로 이력서 재구성", use_container_width=True):
            with st.spinner("이력서를 재구성하는 중..."):
                # 수정된 섹션들을 합쳐 새 이력서 생성
                import json
                reconstructed_resume = call_anthropic_api(
                    prompt=f"""
                    다음은 이력서의 각 섹션입니다. 이 섹션들을 자연스럽게 통합하여 완성된 이력서를 만들어주세요.
                    
                    {json.dumps(st.session_state.resume_sections, indent=2, ensure_ascii=False)}
