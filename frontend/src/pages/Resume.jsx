import { useState, useRef, useEffect } from 'react'
import { Upload, FileText, Loader2, CheckCircle, AlertCircle, User, Briefcase, GraduationCap, Code, Sparkles, Cpu, FolderKanban, Award, Languages, Link2, Target, List, Plus, Edit3, Trash2, Eye, ChevronLeft, Calendar, MapPin } from 'lucide-react'
import { resumeApi } from '../api'

export default function Resume() {
  // 视图模式: 'list' | 'upload' | 'view' | 'edit'
  const [viewMode, setViewMode] = useState('list')
  const [resumes, setResumes] = useState([])
  const [loadingList, setLoadingList] = useState(true)
  const [selectedResume, setSelectedResume] = useState(null)
  
  // 上传相关状态
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [dragActive, setDragActive] = useState(false)
  const [useLlm, setUseLlm] = useState(false)
  const inputRef = useRef(null)

  // 加载简历列表
  useEffect(() => {
    loadResumes()
  }, [])

  const loadResumes = async () => {
    setLoadingList(true)
    try {
      const res = await resumeApi.list()
      setResumes(res.items || [])
    } catch (err) {
      console.error('加载简历列表失败:', err)
    } finally {
      setLoadingList(false)
    }
  }

  const handleDrag = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0])
    }
  }

  const handleChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0])
    }
  }

  const handleFile = (f) => {
    const validTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
    if (!validTypes.includes(f.type)) {
      setError('请上传 PDF 或 DOCX 格式的简历')
      return
    }
    setFile(f)
    setError(null)
  }

  const handleUpload = async () => {
    if (!file) return
    
    setLoading(true)
    setError(null)
    
    try {
      const res = await resumeApi.upload(file, useLlm)
      setResult(res)
      setFile(null)
      // 上传成功后刷新列表
      loadResumes()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // 查看简历详情
  const handleViewResume = async (resume) => {
    try {
      const detail = await resumeApi.get(resume.id)
      setSelectedResume(detail)
      setViewMode('view')
    } catch (err) {
      setError(err.message)
    }
  }

  // 返回列表
  const handleBackToList = () => {
    setViewMode('list')
    setSelectedResume(null)
    setResult(null)
    setFile(null)
    setError(null)
  }

  // 渲染简历列表
  const renderResumeList = () => (
    <div className="animate-fade-in">
      {/* 标题和操作栏 */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold mb-2">简历管理</h1>
          <p className="text-gray-500">管理您的所有简历，支持上传、查看和编辑</p>
        </div>
        <button
          onClick={() => setViewMode('upload')}
          className="btn-primary flex items-center gap-2"
        >
          <Plus size={18} />
          上传简历
        </button>
      </div>

      {/* 加载状态 */}
      {loadingList ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 size={32} className="animate-spin text-primary-500" />
        </div>
      ) : resumes.length === 0 ? (
        <div className="card p-12 text-center">
          <FileText size={48} className="mx-auto text-gray-300 mb-4" />
          <p className="text-gray-500">暂无简历</p>
          <p className="text-sm text-gray-400 mt-1">点击上方按钮上传您的第一份简历</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {resumes.map((resume) => {
            const data = resume.structured_data || {}
            return (
              <div
                key={resume.id}
                className="card p-5 hover:border-primary-300 hover:shadow-md transition-all cursor-pointer"
                onClick={() => handleViewResume(resume)}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 rounded-full bg-primary-100 flex items-center justify-center">
                        <User size={24} className="text-primary-600" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-lg">{data.name || '未知姓名'}</h3>
                        <p className="text-gray-500 text-sm">{data.current_position || '未填写职位'}</p>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-4 mt-3 text-sm text-gray-600">
                      {data.years_experience && (
                        <span className="flex items-center gap-1">
                          <Briefcase size={14} />
                          {data.years_experience}年经验
                        </span>
                      )}
                      {data.location && (
                        <span className="flex items-center gap-1">
                          <MapPin size={14} />
                          {data.location}
                        </span>
                      )}
                      {data.education && (
                        <span className="flex items-center gap-1">
                          <GraduationCap size={14} />
                          {data.education}
                        </span>
                      )}
                    </div>

                    {/* 技能标签 */}
                    {data.skills && (
                      <div className="flex flex-wrap gap-1.5 mt-3">
                        {(Array.isArray(data.skills) 
                          ? data.skills 
                          : [...(data.skills.programming_languages || []), ...(data.skills.frameworks || [])]
                        ).slice(0, 6).map((skill, i) => (
                          <span key={i} className="px-2 py-0.5 bg-primary-50 text-primary-600 text-xs rounded">
                            {skill}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="text-right flex-shrink-0">
                    <p className="text-xs text-gray-400">
                      {resume.file_name}
                    </p>
                    <p className="text-xs text-gray-400 mt-1 flex items-center gap-1 justify-end">
                      <Calendar size={12} />
                      {new Date(resume.created_at).toLocaleDateString()}
                    </p>
                    <div className="flex items-center gap-1 mt-2 justify-end">
                      <span className={`px-2 py-0.5 text-xs rounded ${
                        resume.extraction_method === 'llm' 
                          ? 'bg-purple-100 text-purple-600' 
                          : 'bg-gray-100 text-gray-600'
                      }`}>
                        {resume.extraction_method === 'llm' ? 'AI解析' : '规则解析'}
                      </span>
                      <span className="px-2 py-0.5 bg-green-100 text-green-600 text-xs rounded">
                        {Math.round(resume.extraction_confidence * 100)}%
                      </span>
                    </div>
                    <p className="text-xs text-primary-500 mt-2">
                      点击查看详情 →
                    </p>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )

  // 渲染上传页面
  const renderUploadPage = () => {
    const data = result?.structured_data || {}
    
    return (
      <div className="animate-fade-in max-w-4xl mx-auto">
        {/* 返回按钮 */}
        <button
          onClick={handleBackToList}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6"
        >
          <ChevronLeft size={20} />
          返回简历列表
        </button>

        {/* 标题 */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold mb-2">上传简历</h1>
          <p className="text-gray-500">上传简历，AI自动解析并提取关键信息</p>
        </div>

        {/* 上传区域 */}
        <div
          className={`card p-8 mb-8 border-2 border-dashed transition-colors
            ${dragActive ? 'border-primary-500 bg-primary-50' : 'border-gray-200'}
            ${file ? 'border-green-500 bg-green-50' : ''}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.docx"
            onChange={handleChange}
            className="hidden"
          />
          
          <div className="text-center">
            {file ? (
              <>
                <FileText size={48} className="mx-auto text-green-500 mb-4" />
                <p className="font-medium text-green-700">{file.name}</p>
                <p className="text-sm text-green-600 mt-1">
                  {(file.size / 1024).toFixed(1)} KB
                </p>
              </>
            ) : (
              <>
                <Upload size={48} className="mx-auto text-gray-300 mb-4" />
                <p className="text-gray-600 mb-2">
                  拖拽文件到这里，或
                  <button
                    onClick={() => inputRef.current?.click()}
                    className="text-primary-600 hover:text-primary-700 font-medium mx-1"
                  >
                    点击上传
                  </button>
                </p>
                <p className="text-sm text-gray-400">支持 PDF、DOCX 格式，最大 10MB</p>
              </>
            )}
          </div>

          {file && (
            <div className="mt-6 space-y-4">
              {/* 解析方式选择 */}
              <div className="flex justify-center">
                <div className="inline-flex rounded-lg border border-gray-200 p-1 bg-gray-50">
                  <button
                    onClick={() => setUseLlm(false)}
                    className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all
                      ${!useLlm 
                        ? 'bg-white text-primary-600 shadow-sm' 
                        : 'text-gray-500 hover:text-gray-700'}`}
                  >
                    <Cpu size={16} />
                    规则解析
                  </button>
                  <button
                    onClick={() => setUseLlm(true)}
                    className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all
                      ${useLlm 
                        ? 'bg-gradient-to-r from-purple-500 to-pink-500 text-white shadow-sm' 
                        : 'text-gray-500 hover:text-gray-700'}`}
                  >
                    <Sparkles size={16} />
                    AI大模型解析
                  </button>
                </div>
              </div>
              
              {/* 解析方式说明 */}
              <p className="text-center text-xs text-gray-400">
                {useLlm 
                  ? '使用AI大模型深度理解简历内容，提取更准确（较慢）' 
                  : '使用规则快速提取简历信息（推荐）'}
              </p>

              {/* 操作按钮 */}
              <div className="flex justify-center gap-4">
                <button
                  onClick={() => setFile(null)}
                  className="btn-secondary"
                >
                  重新选择
                </button>
                <button
                  onClick={handleUpload}
                  disabled={loading}
                  className="btn-primary flex items-center gap-2"
                >
                  {loading ? (
                    <>
                      <Loader2 size={18} className="animate-spin" />
                      {useLlm ? 'AI解析中...' : '解析中...'}
                    </>
                  ) : (
                    <>
                      {useLlm ? <Sparkles size={18} /> : <Upload size={18} />}
                      上传并解析
                    </>
                  )}
                </button>
              </div>
            </div>
          )}
        </div>

        {/* 错误提示 */}
        {error && (
          <div className="card p-4 mb-6 bg-red-50 border-red-100 flex items-start gap-3">
            <AlertCircle className="text-red-500 flex-shrink-0 mt-0.5" size={20} />
            <div>
              <p className="font-medium text-red-800">上传失败</p>
              <p className="text-sm text-red-600 mt-1">{error}</p>
            </div>
          </div>
        )}

        {/* 解析结果 */}
        {result && renderResumeDetail(data, result)}
      </div>
    )
  }

  // 渲染简历详情
  const renderResumeDetail = (data, resumeInfo) => (
    <div className="animate-fade-in">
      <div className="card p-4 mb-6 bg-green-50 border-green-100 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <CheckCircle className="text-green-500" size={24} />
          <div>
            <p className="font-medium text-green-800">解析成功</p>
            <p className="text-sm text-green-600">
              提取方法: {resumeInfo.extraction_method === 'llm' ? 'AI大模型' : '规则提取'} | 
              置信度: {(resumeInfo.extraction_confidence * 100).toFixed(0)}%
            </p>
          </div>
        </div>
        {resumeInfo.extraction_method !== 'llm' && (
          <button
            onClick={async () => {
              setLoading(true)
              try {
                const res = await resumeApi.extractWithLlm(resumeInfo.id)
                if (viewMode === 'view') {
                  setSelectedResume(res)
                } else {
                  setResult(res)
                }
                loadResumes()
              } catch (err) {
                setError(err.message)
              } finally {
                setLoading(false)
              }
            }}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-1.5 text-sm bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {loading ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Sparkles size={14} />
            )}
            用AI重新解析
          </button>
        )}
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* 基本信息 */}
        <div className="card p-6">
          <h3 className="font-semibold flex items-center gap-2 mb-4">
            <User size={18} className="text-primary-500" />
            基本信息
          </h3>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">姓名</span>
              <span className="font-medium">{data.name || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">电话</span>
              <span className="font-medium">{data.phone || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">邮箱</span>
              <span className="font-medium">{data.email || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">所在城市</span>
              <span className="font-medium">{data.location || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">工作年限</span>
              <span className="font-medium">{data.years_experience ? `${data.years_experience} 年` : '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">当前职位</span>
              <span className="font-medium">{data.current_position || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">当前公司</span>
              <span className="font-medium">{data.current_company || '-'}</span>
            </div>
          </div>
        </div>

        {/* 教育背景 */}
        <div className="card p-6">
          <h3 className="font-semibold flex items-center gap-2 mb-4">
            <GraduationCap size={18} className="text-primary-500" />
            教育背景
          </h3>
          {(data.education_list?.length > 0 || data.education) ? (
            <div className="space-y-4">
              {data.education_list?.map((edu, i) => (
                <div key={i} className="text-sm border-l-2 border-primary-200 pl-3">
                  <p className="font-medium">{edu.school}</p>
                  <p className="text-gray-600">{edu.major} · {edu.degree}</p>
                  {(edu.start_date || edu.end_date) && (
                    <p className="text-gray-400 text-xs">{edu.start_date} - {edu.end_date || '至今'}</p>
                  )}
                  {edu.gpa && <p className="text-gray-500 text-xs">GPA: {edu.gpa}</p>}
                </div>
              ))}
              {!data.education_list?.length && data.education && (
                <div className="text-sm">
                  <p className="font-medium">{data.university || '-'}</p>
                  <p className="text-gray-500">{data.major} · {data.education}</p>
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-gray-400">暂无教育信息</p>
          )}
        </div>

        {/* 工作经历 */}
        <div className="card p-6 md:col-span-2">
          <h3 className="font-semibold flex items-center gap-2 mb-4">
            <Briefcase size={18} className="text-primary-500" />
            工作经历
          </h3>
          {data.work_experiences?.length > 0 ? (
            <div className="space-y-5">
              {data.work_experiences.map((exp, i) => (
                <div key={i} className="text-sm border-l-2 border-blue-200 pl-4">
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="font-medium text-base">{exp.position || exp.description}</p>
                      <p className="text-gray-600">{exp.company}</p>
                    </div>
                    <span className="text-gray-400 text-xs whitespace-nowrap">
                      {exp.start_date || exp.period} - {exp.end_date || ''}
                    </span>
                  </div>
                  {exp.department && <p className="text-gray-500 text-xs mt-1">{exp.department}</p>}
                  {exp.responsibilities?.length > 0 && (
                    <ul className="mt-2 text-gray-600 space-y-1">
                      {exp.responsibilities.slice(0, 3).map((r, j) => (
                        <li key={j} className="flex items-start gap-2">
                          <span className="text-primary-400 mt-1">•</span>
                          <span>{r}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                  {exp.achievements?.length > 0 && (
                    <div className="mt-2">
                      <span className="text-xs text-green-600 font-medium">业绩亮点：</span>
                      <ul className="text-gray-600 space-y-1">
                        {exp.achievements.slice(0, 2).map((a, j) => (
                          <li key={j} className="flex items-start gap-2">
                            <span className="text-green-400 mt-1">✓</span>
                            <span>{a}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-400">暂无工作经历</p>
          )}
        </div>

        {/* 项目经历 */}
        <div className="card p-6 md:col-span-2">
          <h3 className="font-semibold flex items-center gap-2 mb-4">
            <FolderKanban size={18} className="text-primary-500" />
            项目经历
          </h3>
          {data.project_experiences?.length > 0 ? (
            <div className="space-y-5">
              {data.project_experiences.map((proj, i) => (
                <div key={i} className="text-sm border-l-2 border-purple-200 pl-4">
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="font-medium text-base">{proj.name}</p>
                      {proj.role && <p className="text-purple-600">{proj.role}</p>}
                    </div>
                    {(proj.start_date || proj.end_date) && (
                      <span className="text-gray-400 text-xs whitespace-nowrap">
                        {proj.start_date} - {proj.end_date || '至今'}
                      </span>
                    )}
                  </div>
                  {proj.description && <p className="text-gray-600 mt-2">{proj.description}</p>}
                  {proj.tech_stack?.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {proj.tech_stack.map((tech, j) => (
                        <span key={j} className="px-2 py-0.5 bg-purple-50 text-purple-600 text-xs rounded">
                          {tech}
                        </span>
                      ))}
                    </div>
                  )}
                  {proj.achievements?.length > 0 && (
                    <ul className="mt-2 text-gray-600 space-y-1">
                      {proj.achievements.map((a, j) => (
                        <li key={j} className="flex items-start gap-2">
                          <span className="text-purple-400 mt-1">★</span>
                          <span>{a}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-400">暂无项目经历</p>
          )}
        </div>

        {/* 技能 */}
        <div className="card p-6">
          <h3 className="font-semibold flex items-center gap-2 mb-4">
            <Code size={18} className="text-primary-500" />
            技能标签
          </h3>
          {(data.skills && (Array.isArray(data.skills) ? data.skills.length > 0 : Object.keys(data.skills).length > 0)) ? (
            <div className="space-y-3">
              {/* 如果是分类的技能对象 */}
              {!Array.isArray(data.skills) ? (
                <>
                  {data.skills.programming_languages?.length > 0 && (
                    <div>
                      <p className="text-xs text-gray-500 mb-1">编程语言</p>
                      <div className="flex flex-wrap gap-1">
                        {data.skills.programming_languages.map((s, i) => (
                          <span key={i} className="px-2 py-1 bg-blue-50 text-blue-600 text-xs rounded-full">{s}</span>
                        ))}
                      </div>
                    </div>
                  )}
                  {data.skills.frameworks?.length > 0 && (
                    <div>
                      <p className="text-xs text-gray-500 mb-1">框架</p>
                      <div className="flex flex-wrap gap-1">
                        {data.skills.frameworks.map((s, i) => (
                          <span key={i} className="px-2 py-1 bg-green-50 text-green-600 text-xs rounded-full">{s}</span>
                        ))}
                      </div>
                    </div>
                  )}
                  {data.skills.databases?.length > 0 && (
                    <div>
                      <p className="text-xs text-gray-500 mb-1">数据库</p>
                      <div className="flex flex-wrap gap-1">
                        {data.skills.databases.map((s, i) => (
                          <span key={i} className="px-2 py-1 bg-orange-50 text-orange-600 text-xs rounded-full">{s}</span>
                        ))}
                      </div>
                    </div>
                  )}
                  {data.skills.tools?.length > 0 && (
                    <div>
                      <p className="text-xs text-gray-500 mb-1">工具/平台</p>
                      <div className="flex flex-wrap gap-1">
                        {data.skills.tools.map((s, i) => (
                          <span key={i} className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded-full">{s}</span>
                        ))}
                      </div>
                    </div>
                  )}
                  {data.skills.other?.length > 0 && (
                    <div>
                      <p className="text-xs text-gray-500 mb-1">其他</p>
                      <div className="flex flex-wrap gap-1">
                        {data.skills.other.map((s, i) => (
                          <span key={i} className="px-2 py-1 bg-primary-50 text-primary-600 text-xs rounded-full">{s}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {data.skills.map((skill, i) => (
                    <span key={i} className="px-3 py-1 bg-primary-50 text-primary-600 text-sm rounded-full">
                      {skill}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-gray-400">暂无技能信息</p>
          )}
        </div>

        {/* 证书 & 语言 & 链接 */}
        <div className="card p-6">
          <div className="space-y-6">
            {/* 证书 */}
            <div>
              <h3 className="font-semibold flex items-center gap-2 mb-3">
                <Award size={18} className="text-primary-500" />
                证书资质
              </h3>
              {data.certifications?.length > 0 ? (
                <div className="space-y-2">
                  {data.certifications.map((cert, i) => (
                    <div key={i} className="text-sm flex justify-between">
                      <span className="font-medium">{cert.name}</span>
                      {cert.date && <span className="text-gray-400 text-xs">{cert.date}</span>}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-400">暂无证书信息</p>
              )}
            </div>

            {/* 语言能力 */}
            <div>
              <h3 className="font-semibold flex items-center gap-2 mb-3">
                <Languages size={18} className="text-primary-500" />
                语言能力
              </h3>
              {data.languages?.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {data.languages.map((lang, i) => (
                    <span key={i} className="px-3 py-1 bg-gray-100 text-gray-700 text-sm rounded-full">
                      {lang.language} · {lang.proficiency}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-400">暂无语言信息</p>
              )}
            </div>

            {/* 链接 */}
            {data.links && Object.keys(data.links).length > 0 && (
              <div>
                <h3 className="font-semibold flex items-center gap-2 mb-3">
                  <Link2 size={18} className="text-primary-500" />
                  相关链接
                </h3>
                <div className="space-y-2">
                  {data.links.github && (
                    <a href={data.links.github} target="_blank" rel="noopener noreferrer" 
                       className="text-sm text-blue-600 hover:underline block">GitHub</a>
                  )}
                  {data.links.linkedin && (
                    <a href={data.links.linkedin} target="_blank" rel="noopener noreferrer"
                       className="text-sm text-blue-600 hover:underline block">LinkedIn</a>
                  )}
                  {data.links.portfolio && (
                    <a href={data.links.portfolio} target="_blank" rel="noopener noreferrer"
                       className="text-sm text-blue-600 hover:underline block">作品集</a>
                  )}
                  {data.links.blog && (
                    <a href={data.links.blog} target="_blank" rel="noopener noreferrer"
                       className="text-sm text-blue-600 hover:underline block">博客</a>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* 求职意向 */}
        {data.job_intention && (
          <div className="card p-6">
            <h3 className="font-semibold flex items-center gap-2 mb-4">
              <Target size={18} className="text-primary-500" />
              求职意向
            </h3>
            <div className="space-y-3 text-sm">
              {data.job_intention.positions?.length > 0 && (
                <div className="flex justify-between">
                  <span className="text-gray-500">期望职位</span>
                  <span className="font-medium">{data.job_intention.positions.join(', ')}</span>
                </div>
              )}
              {data.job_intention.cities?.length > 0 && (
                <div className="flex justify-between">
                  <span className="text-gray-500">期望城市</span>
                  <span className="font-medium">{data.job_intention.cities.join(', ')}</span>
                </div>
              )}
              {(data.job_intention.salary_min || data.job_intention.salary_max) && (
                <div className="flex justify-between">
                  <span className="text-gray-500">期望薪资</span>
                  <span className="font-medium">
                    {data.job_intention.salary_min}K - {data.job_intention.salary_max}K
                  </span>
                </div>
              )}
              {data.job_intention.job_type && (
                <div className="flex justify-between">
                  <span className="text-gray-500">工作类型</span>
                  <span className="font-medium">{data.job_intention.job_type}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* 自我评价 */}
        {data.self_evaluation && (
          <div className="card p-6 md:col-span-2">
            <h3 className="font-semibold flex items-center gap-2 mb-4">
              <User size={18} className="text-primary-500" />
              自我评价
            </h3>
            <p className="text-sm text-gray-600 leading-relaxed whitespace-pre-wrap">
              {data.self_evaluation}
            </p>
          </div>
        )}
      </div>
    </div>
  )

  // 渲染查看页面
  const renderViewPage = () => {
    if (!selectedResume) return null
    const data = selectedResume.structured_data || {}
    
    return (
      <div className="animate-fade-in max-w-4xl mx-auto">
        {/* 返回按钮 */}
        <button
          onClick={handleBackToList}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6"
        >
          <ChevronLeft size={20} />
          返回简历列表
        </button>

        {/* 标题 */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold mb-2">{data.name || '简历详情'}</h1>
          <p className="text-gray-500">{selectedResume.file_name}</p>
        </div>

        {renderResumeDetail(data, selectedResume)}
      </div>
    )
  }

  // 根据视图模式渲染不同内容
  switch (viewMode) {
    case 'list':
      return renderResumeList()
    case 'upload':
      return renderUploadPage()
    case 'view':
      return renderViewPage()
    default:
      return renderResumeList()
  }
}
