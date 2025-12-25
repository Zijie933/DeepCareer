import { useState, useEffect } from 'react'
import { Search, MapPin, Building2, Briefcase, Filter, Loader2, ExternalLink, X, ChevronDown, RefreshCw } from 'lucide-react'
import { jobApi, crawlerApi } from '../api'

export default function Jobs() {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  
  // 搜索和筛选状态
  const [keyword, setKeyword] = useState('')
  const [showFilters, setShowFilters] = useState(false)
  const [filters, setFilters] = useState({
    city: '',
    experience: '',
    education: '',
  })
  
  // 城市列表
  const [cities, setCities] = useState([])
  
  // 经验和学历选项
  const experienceOptions = ['不限', '在校生', '应届生', '1年以内', '1-3年', '3-5年', '5-10年', '10年以上']
  const educationOptions = ['不限', '大专', '本科', '硕士', '博士']

  useEffect(() => {
    loadCities()
  }, [])

  useEffect(() => {
    loadJobs()
  }, [page])

  const loadCities = async () => {
    try {
      const res = await crawlerApi.getCities()
      setCities(Object.keys(res.cities || {}))
    } catch (err) {
      console.error('加载城市列表失败:', err)
    }
  }

  const loadJobs = async () => {
    setLoading(true)
    try {
      const params = {
        skip: (page - 1) * 20,
        limit: 20,
      }
      
      // 添加搜索关键词
      if (keyword.trim()) {
        params.keyword = keyword.trim()
      }
      
      // 添加筛选条件
      if (filters.city && filters.city !== '不限') {
        params.city = filters.city
      }
      if (filters.experience && filters.experience !== '不限') {
        params.experience = filters.experience
      }
      if (filters.education && filters.education !== '不限') {
        params.education = filters.education
      }
      
      const res = await jobApi.list(params)
      setJobs(res.items || [])
      setTotal(res.total || 0)
    } catch (err) {
      console.error('加载职位失败:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (e) => {
    e.preventDefault()
    setPage(1)
    loadJobs()
  }

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }))
  }

  const applyFilters = () => {
    setPage(1)
    loadJobs()
    setShowFilters(false)
  }

  const clearFilters = () => {
    setFilters({ city: '', experience: '', education: '' })
    setKeyword('')
    setPage(1)
    setTimeout(loadJobs, 0)
  }

  // 检查是否有活跃的筛选条件
  const hasActiveFilters = keyword || filters.city || filters.experience || filters.education

  // 点击职位跳转
  const handleJobClick = (job) => {
    if (job.job_url) {
      window.open(job.job_url, '_blank', 'noopener,noreferrer')
    }
  }

  return (
    <div className="animate-fade-in">
      {/* 标题 */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold mb-2">职位库</h1>
        <p className="text-gray-500">浏览已爬取的所有职位信息，支持搜索和筛选</p>
      </div>

      {/* 搜索栏 */}
      <form onSubmit={handleSearch} className="card p-4 mb-6">
        <div className="flex gap-4">
          <div className="flex-1 relative">
            <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              className="input pl-10"
              placeholder="搜索职位名称、公司..."
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
            />
          </div>
          <button type="submit" className="btn-primary">
            搜索
          </button>
          <button 
            type="button" 
            className={`btn-secondary flex items-center gap-2 ${showFilters ? 'bg-primary-50 border-primary-300' : ''}`}
            onClick={() => setShowFilters(!showFilters)}
          >
            <Filter size={18} />
            筛选
            <ChevronDown size={16} className={`transition-transform ${showFilters ? 'rotate-180' : ''}`} />
          </button>
        </div>

        {/* 筛选面板 */}
        {showFilters && (
          <div className="mt-4 pt-4 border-t border-gray-100 animate-fade-in">
            <div className="grid md:grid-cols-3 gap-4">
              {/* 城市筛选 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">城市</label>
                <select
                  className="input"
                  value={filters.city}
                  onChange={(e) => handleFilterChange('city', e.target.value)}
                >
                  <option value="">不限</option>
                  {cities.map(city => (
                    <option key={city} value={city}>{city}</option>
                  ))}
                </select>
              </div>

              {/* 经验筛选 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">经验要求</label>
                <select
                  className="input"
                  value={filters.experience}
                  onChange={(e) => handleFilterChange('experience', e.target.value)}
                >
                  {experienceOptions.map(exp => (
                    <option key={exp} value={exp === '不限' ? '' : exp}>{exp}</option>
                  ))}
                </select>
              </div>

              {/* 学历筛选 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">学历要求</label>
                <select
                  className="input"
                  value={filters.education}
                  onChange={(e) => handleFilterChange('education', e.target.value)}
                >
                  {educationOptions.map(edu => (
                    <option key={edu} value={edu === '不限' ? '' : edu}>{edu}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex justify-end gap-2 mt-4">
              <button
                type="button"
                className="btn-secondary text-sm"
                onClick={clearFilters}
              >
                清除筛选
              </button>
              <button
                type="button"
                className="btn-primary text-sm"
                onClick={applyFilters}
              >
                应用筛选
              </button>
            </div>
          </div>
        )}
      </form>

      {/* 活跃筛选条件标签 */}
      {hasActiveFilters && (
        <div className="flex flex-wrap items-center gap-2 mb-4">
          <span className="text-sm text-gray-500">当前筛选：</span>
          {keyword && (
            <span className="inline-flex items-center gap-1 px-2 py-1 bg-primary-50 text-primary-600 text-sm rounded-full">
              关键词: {keyword}
              <button onClick={() => { setKeyword(''); loadJobs() }} className="hover:text-primary-800">
                <X size={14} />
              </button>
            </span>
          )}
          {filters.city && (
            <span className="inline-flex items-center gap-1 px-2 py-1 bg-blue-50 text-blue-600 text-sm rounded-full">
              城市: {filters.city}
              <button onClick={() => { handleFilterChange('city', ''); setTimeout(loadJobs, 0) }} className="hover:text-blue-800">
                <X size={14} />
              </button>
            </span>
          )}
          {filters.experience && (
            <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-50 text-green-600 text-sm rounded-full">
              经验: {filters.experience}
              <button onClick={() => { handleFilterChange('experience', ''); setTimeout(loadJobs, 0) }} className="hover:text-green-800">
                <X size={14} />
              </button>
            </span>
          )}
          {filters.education && (
            <span className="inline-flex items-center gap-1 px-2 py-1 bg-orange-50 text-orange-600 text-sm rounded-full">
              学历: {filters.education}
              <button onClick={() => { handleFilterChange('education', ''); setTimeout(loadJobs, 0) }} className="hover:text-orange-800">
                <X size={14} />
              </button>
            </span>
          )}
          <button
            onClick={clearFilters}
            className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1"
          >
            <RefreshCw size={14} />
            清除全部
          </button>
        </div>
      )}

      {/* 统计信息 */}
      {!loading && (
        <div className="flex items-center justify-between mb-4">
          <p className="text-sm text-gray-500">
            共找到 <span className="font-semibold text-gray-700">{total}</span> 个职位
          </p>
        </div>
      )}

      {/* 加载状态 */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 size={32} className="animate-spin text-primary-500" />
        </div>
      ) : jobs.length === 0 ? (
        <div className="card p-12 text-center">
          <Briefcase size={48} className="mx-auto text-gray-300 mb-4" />
          <p className="text-gray-500">
            {hasActiveFilters ? '没有找到符合条件的职位' : '暂无职位数据'}
          </p>
          <p className="text-sm text-gray-400 mt-1">
            {hasActiveFilters ? '请尝试调整筛选条件' : '请先使用爬取功能获取职位'}
          </p>
          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="mt-4 btn-secondary text-sm"
            >
              清除筛选条件
            </button>
          )}
        </div>
      ) : (
        <>
          {/* 职位列表 */}
          <div className="grid gap-4">
            {jobs.map((job) => (
              <div 
                key={job.id} 
                className={`card p-5 transition-all ${job.job_url ? 'hover:border-primary-300 hover:shadow-md cursor-pointer' : ''}`}
                onClick={() => handleJobClick(job)}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className={`font-semibold text-lg ${job.job_url ? 'hover:text-primary-600' : ''} transition-colors`}>
                        {job.title}
                      </h3>
                      {job.job_url && (
                        <ExternalLink size={14} className="text-gray-400 flex-shrink-0" />
                      )}
                    </div>
                    
                    <div className="flex items-center gap-4 mt-2 text-gray-600">
                      <span className="flex items-center gap-1">
                        <Building2 size={14} />
                        {job.company_name}
                      </span>
                      {job.city && (
                        <span className="flex items-center gap-1">
                          <MapPin size={14} />
                          {job.city}
                        </span>
                      )}
                    </div>

                    <div className="flex flex-wrap gap-2 mt-3">
                      {job.experience_required && (
                        <span className="px-2 py-0.5 bg-gray-100 text-gray-600 text-sm rounded">
                          {job.experience_required}
                        </span>
                      )}
                      {job.education_required && (
                        <span className="px-2 py-0.5 bg-gray-100 text-gray-600 text-sm rounded">
                          {job.education_required}
                        </span>
                      )}
                    </div>

                    {(job.structured_data?.required_skills?.length > 0 || job.structured_data?.job_keywords?.length > 0) && (
                      <div className="flex flex-wrap gap-1.5 mt-3">
                        {(job.structured_data.required_skills || job.structured_data.job_keywords || []).slice(0, 6).map((kw, i) => (
                          <span key={i} className="px-2 py-0.5 bg-primary-50 text-primary-600 text-xs rounded">
                            {kw}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="text-right flex-shrink-0">
                    <p className="text-lg font-semibold text-primary-600">
                      {job.salary_text || '面议'}
                    </p>
                    <p className="text-xs text-gray-400 mt-2">
                      {job.platform}
                    </p>
                    {job.job_url && (
                      <p className="text-xs text-primary-500 mt-1">
                        点击查看详情 →
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* 分页 */}
          {total > 20 && (
            <div className="flex items-center justify-center gap-2 mt-8">
              <button
                className="btn-secondary"
                disabled={page === 1}
                onClick={() => setPage(p => p - 1)}
              >
                上一页
              </button>
              <span className="px-4 text-gray-600">
                第 {page} 页 / 共 {Math.ceil(total / 20)} 页
              </span>
              <button
                className="btn-secondary"
                disabled={jobs.length < 20}
                onClick={() => setPage(p => p + 1)}
              >
                下一页
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
