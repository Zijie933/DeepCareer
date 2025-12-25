import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 响应拦截器
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message = error.response?.data?.detail || error.message || '请求失败'
    return Promise.reject(new Error(message))
  }
)

// 爬虫相关API
export const crawlerApi = {
  // 爬取职位
  searchJobs: (params) => api.post('/crawler/boss/search', params),
  
  // 测试爬虫
  testCrawler: () => api.get('/crawler/boss/test'),
  
  // 获取支持的城市
  getCities: () => api.get('/crawler/cities'),
}

// 职位相关API (V2)
export const jobApi = {
  // 获取职位列表
  list: (params) => api.get('/v2/jobs', { params }),
  
  // 获取职位详情
  get: (id) => api.get(`/v2/jobs/${id}`),
  
  // 搜索职位
  search: (params) => api.post('/v2/jobs/search', params),
  
  // 创建职位
  create: (data) => api.post('/v2/jobs', data),
}

// 简历相关API (V2)
export const resumeApi = {
  // 上传简历
  upload: (file, useLlm = false) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('use_llm', useLlm)
    return api.post('/v2/resumes/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  
  // 获取简历列表
  list: () => api.get('/v2/resumes'),
  
  // 获取简历详情
  get: (id) => api.get(`/v2/resumes/${id}`),
  
  // 确认简历
  confirm: (id, data) => api.put(`/v2/resumes/${id}/confirm`, data),
  
  // 使用大模型重新解析
  extractWithLlm: (id) => api.post(`/v2/resumes/${id}/extract-with-llm`),
}

// 匹配相关API (V2)
export const matchApi = {
  // 快速匹配
  fast: (resumeId, topK = 10) => api.post('/v2/match/fast', {
    resume_id: resumeId,
    top_k: topK,
  }),
  
  // 精细匹配
  precise: (resumeId, jobId) => api.post('/v2/match/precise', {
    resume_id: resumeId,
    job_id: jobId,
  }),
  
  // 获取匹配历史
  history: (resumeId) => api.get(`/v2/match/history/${resumeId}`),
}

// 智能匹配API
export const smartMatchApi = {
  // 获取可用简历列表
  getResumes: () => api.get('/v2/smart-match/resumes'),
  
  // 获取简历推荐关键词
  getKeywords: (resumeId) => api.get(`/v2/smart-match/keywords/${resumeId}`),
  
  // 执行智能匹配（非流式）
  match: (params) => api.post('/v2/smart-match/', params),
  
  // 流式智能匹配（SSE）
  matchStream: (params, callbacks) => {
    const { onDbMatches, onCrawling, onCrawlerMatch, onComplete, onError } = callbacks
    
    // 使用 fetch 发起 SSE 请求
    const controller = new AbortController()
    
    fetch('/api/v2/smart-match/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
      signal: controller.signal
    }).then(async response => {
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              switch (data.type) {
                case 'db_matches':
                  onDbMatches?.(data.data)
                  break
                case 'crawling':
                  onCrawling?.(data.message, data.needed)
                  break
                case 'crawler_match':
                  onCrawlerMatch?.(data.data)
                  break
                case 'complete':
                  onComplete?.(data.message, data.total_qualified)
                  break
                case 'error':
                  onError?.(data.message)
                  break
              }
            } catch (e) {
              console.error('SSE parse error:', e)
            }
          }
        }
      }
    }).catch(err => {
      if (err.name !== 'AbortError') {
        onError?.(err.message)
      }
    })
    
    // 返回取消函数
    return () => controller.abort()
  }
}

export default api
