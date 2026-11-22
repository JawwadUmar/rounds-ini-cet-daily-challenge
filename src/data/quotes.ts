import { ordinal } from '../core/dates';

export interface Quote {
  text: string;
  author: string;
}

export const quotes: readonly Quote[] = [
  { text: 'The good physician treats the disease; the great physician treats the patient who has the disease.', author: 'William Osler' },
  { text: 'Wherever the art of medicine is loved, there is also a love of humanity.', author: 'Hippocrates' },
  { text: 'To cure sometimes, to relieve often, to comfort always.', author: 'Edward Livingston Trudeau' },
  { text: 'People pay the doctor for his trouble; for his kindness they still remain in his debt.', author: 'Seneca' },
  { text: 'The best doctor gives the least medicines.', author: 'Benjamin Franklin' },
  { text: 'It is much more important to know what sort of a patient has a disease than what sort of a disease a patient has.', author: 'William Osler' },
  { text: 'Listen to the patient, they are telling you the diagnosis.', author: 'William Osler' },
  { text: 'Observation, Reason, Human Understanding, Courage; these make the physician.', author: 'Martin H. Fischer' },
  { text: 'Medicine is a science of uncertainty and an art of probability.', author: 'William Osler' },
  { text: 'The physician should not treat the disease but the patient who is suffering from it.', author: 'Maimonides' },
  { text: "A good doctor's comforting and reassuring words are sometimes more powerful than the medicines.", author: 'Unknown' },
  { text: 'The aim of medicine is to prevent disease and prolong life; the ideal of medicine is to eliminate the need of a physician.', author: 'William J. Mayo' },
  { text: 'Not all angels have wings; some have stethoscopes.', author: 'Unknown' },
  { text: 'Medicines cure diseases, but only doctors can cure patients.', author: 'Carl Jung' },
  { text: 'Wear the white coat with dignity and pride—it is an honor and privilege to get to serve the public as a physician.', author: 'Bill H. Warren' },
  { text: 'A doctor, like anyone else who has to deal with human beings, each of them unique, cannot be a scientist; he is either, like the surgeon, a craftsman, or, like the physician and the psychologist, an artist.', author: 'W. H. Auden' },
  { text: "Time and health are two precious assets that we don't recognize and appreciate until they have been depleted.", author: 'Denis Waitley' },
  { text: 'Nature, time and patience are the three great physicians.', author: 'Bulgarian Proverb' },
];

const firstQuoteDay = ordinal('2026-01-01');
const quoteOrders: number[][] = [];

function shuffledOrder(cycle: number): number[] {
  let seed = (0x9e3779b9 + cycle) >>> 0;
  const random = () => {
    seed = (seed + 0x6d2b79f5) >>> 0;
    let value = seed;
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4_294_967_296;
  };

  const order = quotes.map((_, index) => index);
  for (let index = order.length - 1; index > 0; index--) {
    const swapIndex = Math.floor(random() * (index + 1));
    [order[index], order[swapIndex]] = [order[swapIndex], order[index]];
  }

  const previousOrder = quoteOrders[cycle - 1];
  if (previousOrder && order.length > 1 && order[0] === previousOrder[previousOrder.length - 1]) {
    [order[0], order[1]] = [order[1], order[0]];
  }
  return order;
}

export function quoteForDay(day: string): Quote {
  if (quotes.length === 0) throw new Error('At least one quote is required');

  const dayOffset = Math.max(0, ordinal(day) - firstQuoteDay);
  const cycle = Math.floor(dayOffset / quotes.length);
  while (quoteOrders.length <= cycle) {
    quoteOrders.push(shuffledOrder(quoteOrders.length));
  }

  const order = quoteOrders[cycle];
  return quotes[order[dayOffset % quotes.length]];
}
