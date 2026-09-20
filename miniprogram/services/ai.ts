import type { AiChatResponse } from '../types/api'
import { request } from './request'

export function adminAiChat(message: string): Promise<AiChatResponse> {
  return request<AiChatResponse>({
    url: '/admin/ai/chat',
    method: 'POST',
    data: { message },
  })
}
