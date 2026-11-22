import assert from 'node:assert/strict';
import { readdir, readFile, stat } from 'node:fs/promises';
import { build } from 'esbuild';

await build({entryPoints:['src/data/bank.ts'],outfile:'.cache/bank.mjs',bundle:true,platform:'node',format:'esm'});
const {fullBank,bank,practiceBank}=await import('../.cache/bank.mjs');
const all=await fullBank();
const counts={2020:184,2021:402,2022:399,2023:398,2024:400,2025:200};
const sessionCounts={
  'May 2025':200,'May 2024':200,'Nov 2024':200,'May 2023':199,'Nov 2023':199,
  'May 2022':200,'Nov 2022':199,'May 2021':199,'Nov 2021':203,'Nov 2020':184,
};
assert.equal(all.length,1983);
assert.equal(bank.length,1983);
assert.equal(practiceBank.length,0);
assert.equal(new Set(all.map(q=>q.id)).size,all.length);
assert.equal(new Set(bank.map(q=>q.id)).size,bank.length);
assert.ok(all.every(q=>q.type==='PYQ'&&q.provenance.includes('INICET')));
const sessions=new Set(Object.keys(sessionCounts));
const subjects=new Set(all.map(q=>q.subject));
assert.equal(subjects.size,19);
const linked=new Set();
for(const [year,count] of Object.entries(counts)) {
  const questions=all.filter(q=>q.examYear===+year);
  assert.equal(questions.length,count);
  assert.deepEqual(questions.map(q=>q.number),Array.from({length:count},(_,i)=>i+1));
  assert.equal(new Set(questions.map(q=>q.subject)).size,19);
  for(const q of questions) {
    assert.equal(q.id,`pyq-${year}-${q.number}`);
    assert.ok(sessions.has(q.paperSession),q.id);
    assert.ok(Number.isInteger(q.printedNumber)&&q.printedNumber>0,q.id);
    assert.ok(q.statement.trim()&&q.explanation.trim(),q.id);
    assert.deepEqual(Object.keys(q.options),['A','B','C','D']);
    assert.ok(Object.values(q.options).every(text=>text.trim()),q.id);
    assert.ok(q.answerText.startsWith('('+q.correct+')'),q.id);
    assert.ok(q.pages.length===2&&q.pages.every(p=>p>=7&&p<=754),q.id);
    assert.equal(q.difficulty,'Medium',q.id);
    assert.equal(q.difficultyEstimated,true,q.id);
    for(const image of q.images??[]) {
      assert.ok(image.src.startsWith(`assets/images/pyq/${year}/${q.paperSession.toLowerCase().replaceAll(' ','-')}/q${q.printedNumber}-`),q.id);
      assert.ok(image.width>0&&image.height>0&&image.alt,q.id);
      assert.ok(!linked.has(image.src),image.src);linked.add(image.src);
      assert.ok((await stat('public/'+image.src)).size>0,image.src);
    }
  }
}
for(const [session,count] of Object.entries(sessionCounts))
  assert.equal(all.filter(q=>q.paperSession===session).length,count,session);
assert.equal(linked.size,409);
assert.equal(all.filter(q=>q.images?.length).length,404);
assert.equal(all.filter(q=>q.reviewOnly).length,9);
assert.equal(all.filter(q=>q.imageUnavailable).length,1);
const imageRoot='public/assets/images/pyq';
for(const year of Object.keys(counts))for(const sitting of await readdir(`${imageRoot}/${year}`)) {
  for(const file of await readdir(`${imageRoot}/${year}/${sitting}`))
    assert.ok(linked.has(`assets/images/pyq/${year}/${sitting}/${file}`),file);
}
const schedule=JSON.parse(await readFile('src/data/schedule-v1.json','utf8'));
assert.equal(schedule.version,'inicet-v1');
assert.equal(schedule.effectiveFrom,'2026-01-01');
assert.equal(schedule.cycleDays,397);
assert.equal(schedule.ids.length,1985);
assert.equal(new Set(schedule.ids.slice(0,1983)).size,1983);
assert.deepEqual(new Set(schedule.ids.slice(0,1983)),new Set(bank.map(q=>q.id)));
assert.equal(new Set(schedule.ids.slice(1983)).size,2);
assert.ok(schedule.ids.slice(1983).every(id=>new Set(schedule.ids.slice(0,1983)).has(id)));
assert.equal(new Set(schedule.ids.slice(-5).map(id=>all.find(q=>q.id===id).subject)).size,5);
console.log('Bank source: 1,983 INICET questions, 10 sittings, 19 subjects, 409 figures and a 397-day rotation.');
