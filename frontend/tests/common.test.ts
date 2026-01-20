import { describe, expect, it } from 'vitest';

import { capitalize } from '../src/util/common';

describe('capitalize', () => {
  it('uppercases the first character', () => {
    expect(capitalize('adventure')).toBe('Adventure');
  });

  it('returns empty string unchanged', () => {
    expect(capitalize('')).toBe('');
  });
});
