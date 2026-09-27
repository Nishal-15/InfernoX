export interface ThermalEvent {
  id: string;
  latitude: number;
  longitude: number;
  detectedAt: string;
  source: string;
  confidence: number;
  frp: number;
  classification?: string;
  aiConfidence?: number;
  priorityScore?: number;
  riskLevel?: 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';
  status: 'NEW' | 'INVESTIGATING' | 'RESOLVED';
}
