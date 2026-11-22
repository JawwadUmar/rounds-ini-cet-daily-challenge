import { createHash } from 'node:crypto';
import { writeFile } from 'node:fs/promises';
import { build } from 'esbuild';

await build({ entryPoints: ['src/data/bank.ts'], outfile: '.cache/full-schedule-bank.mjs', bundle: true, platform: 'node', format: 'esm' });
const { bank } = await import('../.cache/full-schedule-bank.mjs');
const hash = value => createHash('sha256').update('rounds-inicet-v1/' + value).digest('hex');
const subjects = [...new Set(bank.map(q => q.subject))].sort((a,b) => hash(a).localeCompare(hash(b),'en'));
const queues = new Map(subjects.map(subject => [subject, bank.filter(q => q.subject === subject).map(q => q.id).sort((a,b) => hash(a).localeCompare(hash(b),'en'))]));
const ids = [];
while (ids.length + 5 <= bank.length) {
  const available = subjects.filter(subject=>queues.get(subject).length)
    .sort((a,b)=>queues.get(b).length-queues.get(a).length || hash(a).localeCompare(hash(b),'en'));
  if (available.length < 5) throw new Error('Fewer than five subjects remain before the final partial day.');
  for (const subject of available.slice(0,5)) ids.push(queues.get(subject).shift());
}
for (const subject of subjects) if (queues.get(subject).length) ids.push(...queues.get(subject));
const byId = new Map(bank.map(q=>[q.id,q]));
const tailSize = bank.length % 5;
const paddedSubjects = new Set(ids.slice(-tailSize).map(id=>byId.get(id).subject));
const padding = [];
for (const id of ids) {
  const subject = byId.get(id).subject;
  if (!paddedSubjects.has(subject)) { padding.push(id); paddedSubjects.add(subject); }
  if (padding.length===((5-tailSize)%5)) break;
}
ids.push(...padding);
const requiredPadding = (5-tailSize)%5;
if (padding.length!==requiredPadding || ids.length % 5 || new Set(ids.slice(0,bank.length)).size !== bank.length || new Set(ids.slice(-5)).size !== 5 || new Set(ids.slice(-5).map(id=>byId.get(id).subject)).size!==5) throw new Error('Incomplete or repeated INICET schedule.');
await writeFile(process.argv[2] ?? 'src/data/schedule-v1.json',JSON.stringify({
  version:'inicet-v1', effectiveFrom:'2026-01-01', cycleDays:ids.length / 5, ids,
},null,2)+'\n',{flag:'w'});
console.log(`Frozen INICET v1: ${bank.length} unique questions, ${ids.length / 5}-day cycle; repeats begin only after full coverage.`);
