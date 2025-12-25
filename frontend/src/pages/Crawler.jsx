import { useState, useEffect } from 'react'
import { Search, MapPin, Hash, Loader2, CheckCircle, AlertCircle, ChevronDown } from 'lucide-react'
import { crawlerApi } from '../api'

const defaultCities = ['北京', '上海', '深圳', '广州', '杭州', '成都', '武汉', '南京', '佛山', '东莞']

export default function Crawler() {
  const [form, setForm] = useState({
    keyword: '',
    city: '深圳',
    max_results: 10,
    fetch_detail: true,
    save_to_db: true,
  })
  const [cities, setCities] = useState({})
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    crawlerApi.getCities().then(res => setCities(res.cities || {})).catch(() => {})
  }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.keyword.trim()) return
    
    setLoading(true)
    setError(null)
    setResult(null)
    
    try {
      const res = await crawlerApi.searchJobs(form)
      setResult(res)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const cityList = Object.keys(cities).length > 0 ? Object.keys(cities) : defaultCities

  return (
    <div className="animate-fade-in max-w-4xl mx-auto">
      {/* 标题 */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold mb-2">职位爬取</h1>
        <p className="text-gray-500">从BOSS直聘爬取最新职位信息并保存到数据库</p>
      </div>

      {/* 搜索表单 */}
      <form onSubmit={handleSubmit} className="card p-6 mb-8">
        <div className="grid md:grid-cols-2 gap-6">
          {/* 关键词 */}
          <div>
            <label className="label">
              <Search size={14} className="inline mr-1" />
              搜索关键词
            </label>
            <input
              type="text"
              className="input"
              placeholder="如：Python、Java、产品经理"
              value={form.keyword}
              onChange={(e) => setForm({ ...form, keyword: e.target.value })}
            />
          </div>

          {/* 城市 */}
          <div>
            <label className="label">
              <MapPin size={14} className="inline mr-1" />
              城市
            </label>
            <div className="relative">
              <select
                className="input appearance-none pr-10"
                value={form.city}
                onChange={(e) => setForm({ ...form, city: e.target.value })}
              >
                {cityList.map(city => (
                  <option key={city} value={city}>{city}</option>
                ))}
              </select>
              <ChevronDown size={18} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
            </div>
          </div>

          {/* 数量 */}
          <div>
            <label className="label">
              <Hash size={14} className="inline mr-1" />
              爬取数量
            </label>
            <input
              type="number"
              className="input"
              min="1"
              max="100"
              value={form.max_results}
              onChange={(e) => setForm({ ...form, max_results: parseInt(e.target.value) || 10 })}
            />
          </div>

          {/* 选项 */}
          <div className="flex items-end gap-6">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                checked={form.fetch_detail}
                onChange={(e) => setForm({ ...form, fetch_detail: e.target.checked })}
              />
              <span className="text-sm text-gray-700">获取详情</span>
            </label>
            
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                checked={form.save_to_db}
                onChange={(e) => setForm({ ...form, save_to_db: e.target.checked })}
              />
              <span className="text-sm text-gray-700">保存到数据库</span>
            </label>
          </div>
        </div>

        <button
          type="submit"
          disabled={loading || !form.keyword.trim()}
          className="btn-primary w-full mt-6 flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <Loader2 size={18} className="animate-spin" />
              爬取中...
            </>
          ) : (
            <>
              <Search size={18} />
              开始爬取
            </>
          )}
        </button>
      </form>

      {/* 错误提示 */}
      {error && (
        <div className="card p-4 mb-6 bg-red-50 border-red-100 flex items-start gap-3">
          <AlertCircle className="text-red-500 flex-shrink-0 mt-0.5" size={20} />
          <div>
            <p className="font-medium text-red-800">爬取失败</p>
            <p className="text-sm text-red-600 mt-1">{error}</p>
          </div>
        </div>
      )}

      {/* 结果展示 */}
      {result && (
        <div className="animate-fade-in">
          {/* 统计 */}
          <div className="card p-4 mb-6 bg-green-50 border-green-100 flex items-center gap-3">
            <CheckCircle className="text-green-500" size={24} />
            <div>
              <p className="font-medium text-green-800">爬取完成</p>
              <p className="text-sm text-green-600">
                找到 {result.total_found} 个职位，保存 {result.saved_count} 个，
                跳过 {result.skipped_count} 个，失败 {result.failed_count} 个
              </p>
            </div>
          </div>

          {/* 职位列表 */}
          <div className="space-y-4">
            {result.jobs?.map((job, idx) => (
              <div key={job.job_id || idx} className="card p-5">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-lg truncate">
                      {job.title}
                    </h3>
                    <p className="text-gray-600 mt-1">
                      {job.company_name || job.company}
                    </p>
                    <div className="flex flex-wrap gap-2 mt-3 text-sm text-gray-500">
                      <span className="px-2 py-0.5 bg-gray-100 rounded">{job.location || job.work_city}</span>
                      <span className="px-2 py-0.5 bg-gray-100 rounded">{job.experience}</span>
                      <span className="px-2 py-0.5 bg-gray-100 rounded">{job.education}</span>
                    </div>
                    {job.job_keywords?.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mt-3">
                        {job.job_keywords.slice(0, 5).map((kw, i) => (
                          <span key={i} className="px-2 py-0.5 bg-primary-50 text-primary-600 text-xs rounded">
                            {kw}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="text-right flex-shrink-0">
                    <p className="text-lg font-semibold text-primary-600">
                      {job.salary_detail || job.salary}
                    </p>
                    {job.saved && (
                      <span className="inline-flex items-center gap-1 text-xs text-green-600 mt-2">
                        <CheckCircle size={12} /> 已保存
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
