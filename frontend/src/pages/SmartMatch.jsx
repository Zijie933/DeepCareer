import { useState, useEffect, useRef } from 'react'
import { 
  Search, FileText, Loader2, CheckCircle, AlertCircle, 
  Briefcase, MapPin, DollarSign, GraduationCap, Clock,
  ExternalLink, Sparkles, Database, Globe, Plus, X, ChevronDown,
  User, Mail, Phone, Code, Building, Eye, RefreshCw
} from 'lucide-react'
import { smartMatchApi, crawlerApi } from '../api'

export default function SmartMatch() {
  // 状态
  const [resumes, setResumes] = useState([])
  const [selectedResume, setSelectedResume] = useState(null)
  const [keywords, setKeywords] = useState([])
  const [extraKeyword, setExtraKeyword] = useState('')
  const [city, setCity] = useState('')
  const [cities, setCities] = useState({})
  const [enableCrawler, setEnableCrawler] = useState(true)
  const [minJobs, setMinJobs] = useState(10)
  
  const [loading, setLoading] = useState(false)
  const [crawling, setCrawling] = useState(false)  // 爬虫进行中
  const [crawlingMessage, setCrawlingMessage] = useState('')
  const [loadingResumes, setLoadingResumes] = useState(true)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  
  const [showResumeDropdown, setShowResumeDropdown] = useState(false)
  const [hoveredResume, setHoveredResume] = useState(null)
  const [previewPosition, setPreviewPosition] = useState({ top: 0, left: 0 })
  const dropdownRef = useRef(null)
  const cancelStreamRef = useRef(null)

  // 处理悬浮预览位置
  const handleResumeHover = (resume, event) => {
    setHoveredResume(resume)
    if (dropdownRef.current) {
      const rect = dropdownRef.current.getBoundingClientRect()
      setPreviewPosition({
        top: rect.top,
        left: rect.right + 10
      })
    }
  }

  // 加载简历列表和城市列表
  useEffect(() => {
    Promise.all([
      smartMatchApi.getResumes(),
      crawlerApi.getCities()
    ]).then(([resumeRes, cityRes]) => {
      setResumes(resumeRes.items || [])
      setCities(cityRes.cities || {})
    }).catch(err => {
      setError('加载数据失败: ' + err.message)
    }).finally(() => {
      setLoadingResumes(false)
    })
    
    // 清理：取消流式请求
    return () => {
      if (cancelStreamRef.current) {
        cancelStreamRef.current()
      }
    }
  }, [])

  // 选择简历后加载推荐关键词
  useEffect(() => {
    if (selectedResume) {
      smartMatchApi.getKeywords(selectedResume.id).then(res => {
        setKeywords(res.keywords || [])
        if (res.suggested_city && !city) {
          setCity(res.suggested_city)
        }
      }).catch(err => {
        console.error('获取关键词失败:', err)
      })
    }
  }, [selectedResume])

  // 添加额外关键词
  const addKeyword = () => {
    if (extraKeyword.trim() && !keywords.includes(extraKeyword.trim())) {
      setKeywords([...keywords, extraKeyword.trim()])
      setExtraKeyword('')
    }
  }

  // 移除关键词
  const removeKeyword = (kw) => {
    setKeywords(keywords.filter(k => k !== kw))
  }

  // 执行流式智能匹配
  const handleMatch = () => {
    if (!selectedResume) {
      setError('请先选择简历')
      return
    }

    setLoading(true)
    setCrawling(false)
    setCrawlingMessage('')
    setError(null)
    setResult(null)

    // 取消之前的请求
    if (cancelStreamRef.current) {
      cancelStreamRef.current()
    }

    // 使用流式API
    cancelStreamRef.current = smartMatchApi.matchStream(
      {
        resume_id: selectedResume.id,
        min_jobs: minJobs,
        max_jobs: 30,
        city: city || null,
        extra_keywords: keywords.length > 0 ? keywords : null,
        enable_crawler: enableCrawler,
        qualified_threshold: 60.0,
        min_display_score: 30.0
      },
      {
        // 数据库匹配结果（第一批）
        onDbMatches: (data) => {
          setLoading(false)
          setResult({
            resume_id: data.resume_id,
            resume_name: data.resume_name,
            target_city: data.target_city,
            search_keywords: data.search_keywords,
            matches: data.matches,
            qualified_count: data.qualified_count,
            from_database: data.from_database,
            from_crawler: 0,
            total_matched: data.matches.length
          })
          
          // 如果需要爬虫
          if (data.need_crawler) {
            setCrawling(true)
            setCrawlingMessage('正在搜索更多职位...')
          }
        },
        
        // 爬虫进度
        onCrawling: (message, needed) => {
          setCrawling(true)
          setCrawlingMessage(message)
        },
        
        // 爬虫找到新职位
        onCrawlerMatch: (match) => {
          setResult(prev => {
            if (!prev) return prev
            
            // 插入到合适的位置（按分数排序，合格的在前）
            const newMatches = [...prev.matches]
            
            if (match.is_qualified) {
              // 合格的插入到合格区域的末尾
              const lastQualifiedIndex = newMatches.findLastIndex(m => m.is_qualified)
              newMatches.splice(lastQualifiedIndex + 1, 0, match)
            } else {
              // 不合格的插入到不合格区域的合适位置
              const insertIndex = newMatches.findIndex(
                m => !m.is_qualified && m.match_score < match.match_score
              )
              if (insertIndex === -1) {
                newMatches.push(match)
              } else {
                newMatches.splice(insertIndex, 0, match)
              }
            }
            
            return {
              ...prev,
              matches: newMatches,
              from_crawler: prev.from_crawler + 1,
              total_matched: newMatches.length,
              qualified_count: match.is_qualified ? prev.qualified_count + 1 : prev.qualified_count
            }
          })
        },
        
        // 完成
        onComplete: (message, totalQualified) => {
          setCrawling(false)
          setCrawlingMessage('')
          setResult(prev => prev ? { ...prev, qualified_count: totalQualified } : prev)
        },
        
        // 错误
        onError: (message) => {
          setLoading(false)
          setCrawling(false)
          setError(message)
        }
      }
    )
  }

  // 获取匹配分数颜色
  const getScoreColor = (score, isQualified) => {
    if (score >= 80) return 'text-green-600 bg-green-50 border-green-200'
    if (score >= 60) return 'text-blue-600 bg-blue-50 border-blue-200'
    if (score >= 40) return 'text-yellow-600 bg-yellow-50 border-yellow-200'
    return 'text-gray-600 bg-gray-50 border-gray-200'
  }

  return (
    <div className="animate-fade-in max-w-6xl mx-auto">
      {/* 标题 */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold mb-2 flex items-center gap-2">
          <Sparkles className="text-primary-500" />
          智能岗位匹配
        </h1>
        <p className="text-gray-500">
          选择简历，AI自动匹配最适合的岗位。数据库不足时自动爬取新职位。
        </p>
      </div>

      {/* 配置区域 */}
      <div className="card p-6 mb-6">
        <h2 className="font-semibold mb-4">匹配配置</h2>
        
        <div className="grid md:grid-cols-2 gap-6">
          {/* 选择简历 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              选择简历 <span className="text-red-500">*</span>
            </label>
            <div className="relative">
              <button
                onClick={() => setShowResumeDropdown(!showResumeDropdown)}
                className="w-full flex items-center justify-between px-4 py-3 border rounded-lg bg-white hover:border-primary-300 transition-colors"
              >
                {selectedResume ? (
                  <div className="flex items-center gap-2">
                    <FileText size={18} className="text-primary-500" />
                    <span>{selectedResume.name}</span>
                    <span className="text-gray-400 text-sm">({selectedResume.file_name})</span>
                  </div>
                ) : (
                  <span className="text-gray-400">请选择简历...</span>
                )}
                <ChevronDown size={18} className="text-gray-400" />
              </button>
              
              {showResumeDropdown && (
                <div 
                  ref={dropdownRef}
                  className="absolute z-10 w-full mt-1 bg-white border rounded-lg shadow-lg max-h-60 overflow-auto"
                  onMouseLeave={() => setHoveredResume(null)}
                >
                  {loadingResumes ? (
                    <div className="p-4 text-center text-gray-500">
                      <Loader2 className="animate-spin mx-auto mb-2" />
                      加载中...
                    </div>
                  ) : resumes.length === 0 ? (
                    <div className="p-4 text-center text-gray-500">
                      暂无简历，请先上传
                    </div>
                  ) : (
                    resumes.map(resume => (
                      <button
                        key={resume.id}
                        onClick={() => {
                          setSelectedResume(resume)
                          setShowResumeDropdown(false)
                          setHoveredResume(null)
                        }}
                        onMouseEnter={(e) => handleResumeHover(resume, e)}
                        className={`w-full px-4 py-3 text-left hover:bg-gray-50 flex items-center justify-between
                          ${selectedResume?.id === resume.id ? 'bg-primary-50' : ''}`}
                      >
                        <div>
                          <p className="font-medium">{resume.name}</p>
                          <p className="text-sm text-gray-500">
                            {resume.current_position || '未知职位'} · {resume.file_name}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          <Eye size={16} className="text-gray-400" />
                          {selectedResume?.id === resume.id && (
                            <CheckCircle size={18} className="text-primary-500" />
                          )}
                        </div>
                      </button>
                    ))
                  )}
                </div>
              )}

              {/* 简历预览弹窗 */}
              {hoveredResume && showResumeDropdown && (
                <ResumePreviewCard 
                  resume={hoveredResume} 
                  position={previewPosition}
                />
              )}
            </div>
          </div>

          {/* 选择城市 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              目标城市
            </label>
            <select
              value={city}
              onChange={(e) => setCity(e.target.value)}
              className="w-full px-4 py-3 border rounded-lg bg-white focus:border-primary-300 focus:ring-1 focus:ring-primary-300"
            >
              <option value="">自动（从简历提取）</option>
              {Object.keys(cities).map(c => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
        </div>

        {/* 搜索关键词 */}
        <div className="mt-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            搜索关键词
            <span className="text-gray-400 font-normal ml-2">（用于爬虫搜索新职位）</span>
          </label>
          <div className="flex flex-wrap gap-2 mb-3">
            {keywords.map((kw, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1 px-3 py-1 bg-primary-50 text-primary-600 rounded-full text-sm"
              >
                {kw}
                <button onClick={() => removeKeyword(kw)} className="hover:text-primary-800">
                  <X size={14} />
                </button>
              </span>
            ))}
            {keywords.length === 0 && (
              <span className="text-gray-400 text-sm">选择简历后自动生成推荐关键词</span>
            )}
          </div>
          <div className="flex gap-2">
            <input
              type="text"
              value={extraKeyword}
              onChange={(e) => setExtraKeyword(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && addKeyword()}
              placeholder="添加额外关键词..."
              className="flex-1 px-4 py-2 border rounded-lg focus:border-primary-300 focus:ring-1 focus:ring-primary-300"
            />
            <button
              onClick={addKeyword}
              className="btn-secondary flex items-center gap-1"
            >
              <Plus size={16} />
              添加
            </button>
          </div>
        </div>

        {/* 高级选项 */}
        <div className="mt-6 flex flex-wrap items-center gap-6">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={enableCrawler}
              onChange={(e) => setEnableCrawler(e.target.checked)}
              className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
            />
            <span className="text-sm text-gray-700">数据库不足时自动爬取新职位</span>
          </label>
          
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-700">最少匹配</span>
            <input
              type="number"
              value={minJobs}
              onChange={(e) => setMinJobs(parseInt(e.target.value) || 10)}
              min={5}
              max={30}
              className="w-16 px-2 py-1 border rounded text-center"
            />
            <span className="text-sm text-gray-700">个岗位</span>
          </div>
        </div>

        {/* 开始匹配按钮 */}
        <div className="mt-6">
          <button
            onClick={handleMatch}
            disabled={loading || crawling || !selectedResume}
            className="btn-primary w-full md:w-auto flex items-center justify-center gap-2 py-3 px-8"
          >
            {loading ? (
              <>
                <Loader2 size={20} className="animate-spin" />
                正在匹配数据库...
              </>
            ) : (
              <>
                <Search size={20} />
                开始智能匹配
              </>
            )}
          </button>
        </div>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="card p-4 mb-6 bg-red-50 border-red-100 flex items-start gap-3">
          <AlertCircle className="text-red-500 flex-shrink-0 mt-0.5" size={20} />
          <div>
            <p className="font-medium text-red-800">匹配失败</p>
            <p className="text-sm text-red-600 mt-1">{error}</p>
          </div>
        </div>
      )}

      {/* 爬虫进度提示 */}
      {crawling && (
        <div className="card p-4 mb-6 bg-purple-50 border-purple-200 flex items-center gap-3 animate-pulse">
          <RefreshCw size={20} className="text-purple-500 animate-spin" />
          <div className="flex-1">
            <p className="font-medium text-purple-800">{crawlingMessage || '正在获取更多职位...'}</p>
            <p className="text-sm text-purple-600 mt-1">新职位将实时添加到下方列表中</p>
          </div>
          <Loader2 size={24} className="text-purple-400 animate-spin" />
        </div>
      )}

      {/* 匹配结果 */}
      {result && (
        <div className="animate-fade-in">
          {/* 结果统计 */}
          <div className={`card p-4 mb-6 ${crawling ? 'bg-blue-50 border-blue-100' : 'bg-green-50 border-green-100'}`}>
            <div className="flex items-center justify-between flex-wrap gap-4">
              <div className="flex items-center gap-3">
                {crawling ? (
                  <RefreshCw className="text-blue-500 animate-spin" size={24} />
                ) : (
                  <CheckCircle className="text-green-500" size={24} />
                )}
                <div>
                  <p className={`font-medium ${crawling ? 'text-blue-800' : 'text-green-800'}`}>
                    {crawling ? '正在匹配中...' : '匹配完成！'}为 {result.resume_name} 找到 {result.total_matched} 个匹配岗位
                    <span className="ml-2 text-sm font-normal">
                      （合格 <span className="text-blue-600 font-semibold">{result.qualified_count}</span> 个，
                      匹配度≥60%）
                    </span>
                  </p>
                  <p className={`text-sm mt-1 ${crawling ? 'text-blue-600' : 'text-green-600'}`}>
                    目标城市: <span className="font-medium">{result.target_city}</span> · 
                    搜索关键词: {result.search_keywords.join(', ')}
                  </p>
                </div>
              </div>
              <div className="flex gap-4 text-sm">
                <div className="flex items-center gap-1 text-blue-600">
                  <Database size={16} />
                  数据库: {result.from_database}
                </div>
                <div className="flex items-center gap-1 text-purple-600">
                  <Globe size={16} />
                  爬虫: {result.from_crawler}
                </div>
              </div>
            </div>
          </div>

          {/* 合格岗位提示 */}
          {result.qualified_count < result.total_matched && (
            <div className="mb-4 px-4 py-2 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-700">
              <span className="font-medium">提示：</span>
              匹配度≥60%的岗位有 {result.qualified_count} 个，其余 {result.total_matched - result.qualified_count} 个为参考推荐（匹配度&lt;60%）
            </div>
          )}

          {/* 岗位列表 */}
          <div className="space-y-4">
            {result.matches.map((job, index) => (
              <div 
                key={job.job_id} 
                className={`card p-5 hover:shadow-md transition-shadow ${
                  !job.is_qualified ? 'opacity-75 border-dashed' : ''
                }`}
              >
                <div className="flex justify-between items-start gap-4">
                  {/* 左侧：岗位信息 */}
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <span className="text-gray-400 text-sm">#{index + 1}</span>
                      <h3 className="font-semibold text-lg">{job.title}</h3>
                      {job.is_qualified ? (
                        <span className="px-2 py-0.5 bg-green-100 text-green-600 text-xs rounded">
                          合格
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 bg-gray-100 text-gray-500 text-xs rounded">
                          参考
                        </span>
                      )}
                      {job.from_crawler && (
                        <span className="px-2 py-0.5 bg-purple-100 text-purple-600 text-xs rounded">
                          新爬取
                        </span>
                      )}
                    </div>
                    
                    <div className="flex items-center gap-4 text-gray-600 mb-3">
                      <span className="flex items-center gap-1">
                        <Briefcase size={16} />
                        {job.company_name}
                      </span>
                      <span className="flex items-center gap-1">
                        <MapPin size={16} />
                        {job.city || '未知'}
                      </span>
                      {job.salary_text && (
                        <span className="flex items-center gap-1 text-orange-600">
                          <DollarSign size={16} />
                          {job.salary_text}
                        </span>
                      )}
                    </div>
                    
                    <div className="flex items-center gap-4 text-sm text-gray-500">
                      {job.experience_required && (
                        <span className="flex items-center gap-1">
                          <Clock size={14} />
                          {job.experience_required}
                        </span>
                      )}
                      {job.education_required && (
                        <span className="flex items-center gap-1">
                          <GraduationCap size={14} />
                          {job.education_required}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* 右侧：匹配分数 */}
                  <div className="text-right">
                    <div className={`inline-block px-4 py-2 rounded-lg border ${getScoreColor(job.match_score, job.is_qualified)}`}>
                      <p className="text-2xl font-bold">{job.match_score}</p>
                      <p className="text-xs">匹配度</p>
                    </div>
                    
                    {job.job_url && (
                      <a
                        href={job.job_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="mt-3 inline-flex items-center gap-1 text-sm text-primary-600 hover:underline"
                      >
                        查看详情
                        <ExternalLink size={14} />
                      </a>
                    )}
                  </div>
                </div>

                {/* 匹配详情（可展开） */}
                {job.match_details && (
                  <details className="mt-4 pt-4 border-t">
                    <summary className="cursor-pointer text-sm text-gray-500 hover:text-gray-700">
                      查看匹配详情
                    </summary>
                    <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                      {job.match_details.dimension_scores && Object.entries(job.match_details.dimension_scores).map(([key, score]) => (
                        <div key={key} className="bg-gray-50 rounded p-2">
                          <p className="text-gray-500 text-xs mb-1">
                            {key === 'skills' ? '技能匹配' :
                             key === 'experience' ? '经验匹配' :
                             key === 'education' ? '学历匹配' :
                             key === 'semantic' ? '语义相似' : key}
                          </p>
                          <p className="font-medium">{typeof score === 'number' ? score.toFixed(1) : score}</p>
                        </div>
                      ))}
                    </div>
                  </details>
                )}
              </div>
            ))}
          </div>

          {result.matches.length === 0 && (
            <div className="card p-8 text-center text-gray-500">
              <Search size={48} className="mx-auto mb-4 text-gray-300" />
              <p>未找到匹配的岗位</p>
              <p className="text-sm mt-2">尝试调整搜索关键词或降低匹配分数要求</p>
            </div>
          )}
        </div>
      )}

      {/* 已选简历预览卡片 */}
      {selectedResume && !showResumeDropdown && (
        <div className="fixed bottom-6 right-6 z-20">
          <ResumePreviewCard resume={selectedResume} isFixed />
        </div>
      )}
    </div>
  )
}

// 简历预览卡片组件
function ResumePreviewCard({ resume, position, isFixed }) {
  const data = resume.structured_data || {}
  
  // 提取技能列表
  const getSkills = () => {
    if (data.skills) {
      if (Array.isArray(data.skills)) return data.skills.slice(0, 8)
      if (typeof data.skills === 'object') {
        const all = [
          ...(data.skills.programming || []),
          ...(data.skills.frameworks || []),
          ...(data.skills.tools || []),
          ...(data.skills.other || [])
        ]
        return all.slice(0, 8)
      }
    }
    return resume.skills?.slice(0, 8) || []
  }

  const skills = getSkills()
  const workExp = data.work_experiences?.[0]
  const education = data.education_list?.[0]

  const cardStyle = isFixed 
    ? {} 
    : { 
        position: 'fixed', 
        top: Math.min(position.top, window.innerHeight - 400),
        left: Math.min(position.left, window.innerWidth - 340),
        zIndex: 50 
      }

  return (
    <div 
      className={`bg-white border rounded-xl shadow-xl w-80 overflow-hidden animate-fade-in ${isFixed ? 'border-primary-200' : ''}`}
      style={cardStyle}
    >
      {/* 头部 */}
      <div className="bg-gradient-to-r from-primary-500 to-primary-600 text-white p-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 bg-white/20 rounded-full flex items-center justify-center">
            <User size={24} />
          </div>
          <div>
            <h3 className="font-semibold text-lg">{resume.name || '未知姓名'}</h3>
            <p className="text-white/80 text-sm">{resume.current_position || data.current_position || '未知职位'}</p>
          </div>
        </div>
      </div>

      {/* 内容 */}
      <div className="p-4 space-y-3 max-h-64 overflow-y-auto">
        {/* 基本信息 */}
        <div className="flex flex-wrap gap-3 text-sm text-gray-600">
          {(resume.email || data.email) && (
            <span className="flex items-center gap-1">
              <Mail size={14} className="text-gray-400" />
              {resume.email || data.email}
            </span>
          )}
          {(resume.phone || data.phone) && (
            <span className="flex items-center gap-1">
              <Phone size={14} className="text-gray-400" />
              {resume.phone || data.phone}
            </span>
          )}
          {(resume.years_experience || data.years_experience) && (
            <span className="flex items-center gap-1">
              <Clock size={14} className="text-gray-400" />
              {resume.years_experience || data.years_experience}年经验
            </span>
          )}
        </div>

        {/* 最近工作 */}
        {workExp && (
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs text-gray-500 mb-1 flex items-center gap-1">
              <Building size={12} />
              最近工作
            </p>
            <p className="font-medium text-sm">{workExp.position || workExp.title}</p>
            <p className="text-gray-600 text-sm">{workExp.company}</p>
            {workExp.duration && (
              <p className="text-gray-400 text-xs mt-1">{workExp.duration}</p>
            )}
          </div>
        )}

        {/* 教育背景 */}
        {education && (
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs text-gray-500 mb-1 flex items-center gap-1">
              <GraduationCap size={12} />
              教育背景
            </p>
            <p className="font-medium text-sm">{education.school}</p>
            <p className="text-gray-600 text-sm">
              {education.major} · {education.degree}
            </p>
          </div>
        )}

        {/* 技能标签 */}
        {skills.length > 0 && (
          <div>
            <p className="text-xs text-gray-500 mb-2 flex items-center gap-1">
              <Code size={12} />
              技能
            </p>
            <div className="flex flex-wrap gap-1">
              {skills.map((skill, i) => (
                <span 
                  key={i}
                  className="px-2 py-0.5 bg-primary-50 text-primary-600 rounded text-xs"
                >
                  {skill}
                </span>
              ))}
              {(resume.skills?.length > 8 || getSkills().length >= 8) && (
                <span className="text-gray-400 text-xs">...</span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* 底部 */}
      {isFixed && (
        <div className="border-t px-4 py-2 bg-gray-50 text-xs text-gray-500 text-center">
          当前选中的简历
        </div>
      )}
    </div>
  )
}
