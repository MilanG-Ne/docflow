import assert from 'node:assert/strict';
import test from 'node:test';
import { hundredths, lineTotal } from '../lib/fees.ts';

test('day rates are parsed to cents without float drift', () => {
  assert.equal(hundredths('1.15'), 115);
  assert.equal(hundredths('650'), 65000);
  assert.equal(hundredths('0.5'), 50);
  for (const value of ['', '-1', '1.005', '1e3', '1000000']) {
    assert.equal(hundredths(value), null);
  }
});

test('fractional days round half up per line, matching the API', () => {
  assert.equal(lineTotal('1.15', 50), 58);
  assert.equal(lineTotal('0.05', 10), 1);
  assert.equal(lineTotal('0.01', 49), 0);
  assert.equal(lineTotal('2.5', 65000), 162500);
  assert.equal(lineTotal('1000', 99999999), 99999999000);
});

test('the editor tolerates an incomplete quantity while typing', () => {
  assert.equal(lineTotal('', 1000), 0);
});
