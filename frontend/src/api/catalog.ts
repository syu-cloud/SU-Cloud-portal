import { apiRequest } from './client'

export type ImageItem = {
  id: string
  name: string
}

export type FlavorItem = {
  id: string
  name: string
  vcpus: number
  ram_mb: number
  disk_gb: number
}

export type ImageListResponse = {
  items: ImageItem[]
}

export type FlavorListResponse = {
  items: FlavorItem[]
}

export function getImages(): Promise<ImageListResponse> {
  return apiRequest<ImageListResponse>('/api/v1/images')
}

export function getFlavors(): Promise<FlavorListResponse> {
  return apiRequest<FlavorListResponse>('/api/v1/flavors')
}
