import type { Question } from './types';
import { dailyPapers } from './pyq/daily';
import { loadPapers } from './pyq';

export const BANK_VERSION = 'inicet-2026-05' as const;
export const practiceBank: readonly Question[] = Object.freeze([]);
export const bank: readonly Question[] = Object.freeze([...dailyPapers]);
export async function fullBank(): Promise<Question[]> { return await loadPapers(); }
export const byId = new Map(bank.map(question => [question.id, question]));
