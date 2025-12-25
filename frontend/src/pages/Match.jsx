import { useState } from 'react'
import { Sparkles, FileText, Target, TrendingUp, Loader2, CheckCircle, Star, ExternalLink, Building2, MapPin } from 'lucide-react'
import { matchApi } from '../api'

export default function Match() {
  const [resumeId, setResumeId] = useState('')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState(null)
  const [error, setError] = useState(null)

  const handleMatch = async () => {
    if (!resumeId) return
    
    setLoading(true)
    setError(null)
    
    try {
      const res = await matchApi.fast(parseInt(resumeId), 10)
      setResults(res)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const getScoreColor = (score) => {
    if (score >= 80) return 'text-green-600 bg-green-50'
    if (score >= 60) return 'text-yellow-600 bg-yellow-50'
    return 'text-gray-600 bg-gray-50'
  }

  // 点击职位跳转
  const handleJobClick = (match) => {
    // 匹配结果可能直接有job_url，或者在job对象里
    const url = match.job_url || match.job?.job_url
    if (url) {
      window.open(url, '_blank', 'noopener,noreferrer')
    }
  }

  return (
    <div className="animate-fade-in max-w-4xl mx-auto">
      {/* 标题 */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold mb-2">智能匹配</h1>
        <p className="text-gray-500">基于7维度算法，为你推荐最匹配的职位</p>
      </div>

      {/* 匹配说明 */}
      <div className="card p-6 mb-8">
        <h3 className="font-semibold mb-4 flex items-center gap-2">
          <Target size={18} className="text-primary-500" />
          7维度匹配算法
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          {[
            { name: '技能匹配', weight: '25%' },
            { name: '经验匹配', weight: '20%' },
            { name: '薪资匹配', weight: '15%' },
            { name: '地点匹配', weight: '10%' },
            { name: '文化匹配', weight: '10%' },
            { name: '成长空间', weight: '10%' },
            { name: '稳定性', weight: '10%' },
          ].map((dim) => (
            <div key={dim.name} className="flex items-center justify-between p-2 bg-gray-50 rounded-lg">
              <span className="text-gray-600">{dim.name}</span>
              <span className="font-medium text-primary-600">{dim.weight}</span>
            </div>
          ))}
        </div>
      </div>

      {/* 匹配表单 */}
      <div className="card p-6 mb-8">
        <label className="label">简历ID</label>
        <div className="flex gap-4">
          <input
            type="text"
            className="input flex-1"
            placeholder="输入简历ID（上传简历后获取）"
            value={resumeId}
            onChange={(e) => setResumeId(e.target.value)}
          />
          <button
            onClick={handleMatch}
            disabled={loading || !resumeId}
            className="btn-primary flex items-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 size={18} className="animate-spin" />
                匹配中...
              </>
            ) : (
              <>
                <Sparkles size={18} />
                开始匹配
              </>
            )}
          </button>
        </div>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="card p-4 mb-6 bg-red-50 border-red-100">
          <p className="text-red-600">{error}</p>
        </div>
      )}

      {/* 匹配结果 */}
      {results && (
        <div className="animate-fade-in">
          <div className="card p-4 mb-6 bg-green-50 border-green-100 flex items-center gap-3">
            <CheckCircle className="text-green-500" size={24} />
            <div>
              <p className="font-medium text-green-800">匹配完成</p>
              <p className="text-sm text-green-600">
                找到 {results.matches?.length || 0} 个匹配职位
              </p>
            </div>
          </div>

          <div className="space-y-4">
            {results.matches?.map((match, idx) => {
              const hasUrl = match.job_url || match.job?.job_url
              return (
                <div 
                  key={match.job_id || idx} 
                  className={`card p-5 transition-all ${hasUrl ? 'hover:border-primary-300 hover:shadow-md cursor-pointer' : ''}`}
                  onClick={() => handleJobClick(match)}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className={`font-semibold text-lg ${hasUrl ? 'hover:text-primary-600' : ''}`}>
                          {match.job_title || match.job?.title}
                        </h3>
                        {hasUrl && (
                          <ExternalLink size={14} className="text-gray-400" />
                        )}
                        <div className={`px-3 py-1 rounded-full text-sm font-medium ${getScoreColor(match.match_score || match.total_score)}`}>
                          <Star size={14} className="inline mr-1" />
                          {(match.match_score || match.total_score)?.toFixed(0)}分
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-4 text-gray-600">
                        <span className="flex items-center gap-1">
                          <Building2 size={14} />
                          {match.company_name || match.job?.company_name}
                        </span>
                        {(match.city || match.job?.city) && (
                          <span className="flex items-center gap-1">
                            <MapPin size={14} />
                            {match.city || match.job?.city}
                          </span>
                        )}
                      </div>
                      
                      <div className="flex flex-wrap gap-2 mt-3 text-sm text-gray-500">
                        {(match.salary_text || match.job?.salary_text) && (
                          <span className="px-2 py-0.5 bg-primary-50 text-primary-600 rounded font-medium">
                            {match.salary_text || match.job?.salary_text}
                          </span>
                        )}
                      </div>

                      {/* 维度得分 */}
                      {match.match_details && (
                        <div className="mt-4 grid grid-cols-4 gap-2 text-xs">
                          {Object.entries(match.match_details.weights || match.match_details || {}).slice(0, 4).map(([key, value]) => (
                            <div key={key} className="text-center">
                              <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden mb-1">
                                <div 
                                  className="h-full bg-primary-500 rounded-full"
                                  style={{ width: `${(value * 100)}%` }}
                                />
                              </div>
                              <span className="text-gray-500">{key}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    <div className="text-right">
                      <TrendingUp size={24} className="text-primary-500 mb-2" />
                      <p className="text-xs text-gray-500">匹配度</p>
                      {hasUrl && (
                        <p className="text-xs text-primary-500 mt-2">
                          点击查看 →
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* 空状态 */}
      {!results && !loading && (
        <div className="card p-12 text-center">
          <Sparkles size={48} className="mx-auto text-gray-300 mb-4" />
          <p className="text-gray-500">输入简历ID开始智能匹配</p>
          <p className="text-sm text-gray-400 mt-1">系统将分析你的简历并推荐最合适的职位</p>
        </div>
      )}
    </div>
  )
}
