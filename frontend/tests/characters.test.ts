import { beforeEach, describe, expect, it, vi } from 'vitest';
import axios from 'axios';

vi.mock('axios', () => ({
  default: {
    get: vi.fn(),
  },
}));

const mockedAxios = axios as unknown as { get: ReturnType<typeof vi.fn> };

describe('fetchCharacterData', () => {
  beforeEach(() => {
    vi.resetModules();
    mockedAxios.get.mockReset();
  });

  it('joins character data with user display names', async () => {
    mockedAxios.get
      .mockResolvedValueOnce({
        data: {
          '1': {
            id: 1,
            name: 'Hero',
            dndbeyond_account: 'player@example.com',
          },
        },
      })
      .mockResolvedValueOnce({
        data: [
          {
            dnd_beyond_name: 'player@example.com',
            display_name: 'Player One',
          },
        ],
      });

    const { fetchCharacterData } = await import('../src/util/characters');
    const data = await fetchCharacterData();

    expect(data[1].player_name).toBe('Player One');
    expect(mockedAxios.get).toHaveBeenCalledTimes(2);
  });

  it('caches results after the first fetch', async () => {
    mockedAxios.get
      .mockResolvedValueOnce({ data: {} })
      .mockResolvedValueOnce({ data: [] });

    const { fetchCharacterData } = await import('../src/util/characters');
    await fetchCharacterData();
    await fetchCharacterData();

    expect(mockedAxios.get).toHaveBeenCalledTimes(2);
  });
});
