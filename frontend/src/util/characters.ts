import axios from 'axios';

export type Character = {
  id: number;
  name: string;
  dndbeyond_account: string;
  player_name?: string;
  campaign: string;
  character_sheet: string;
  avatar: string;
  race: string;
  base_race: string;
  class_description: string;
  classes: { [class_: string]: number };
  level: number;
  alignment: string;
  age: string;
  hair: string;
  eyes: string;
  skin: string;
  height: string;
  personality_traits: string;
  ideals: string;
  bonds: string;
  flaws: string;
  appearance: string;
  personal_possessions: string;
  organizations: string;
  allies: string;
  enemies: string;
  backstory: string;
  other_notes: string;
};

let cache = null as null | { [id: number]: Character };

export async function fetchCharacterData(): Promise<{
  [id: number]: Character;
}> {
  if (cache !== null) {
    return new Promise((resolve) => resolve(cache!));
  }
  cache = await fetchAndJoin();
  return cache;
}

async function fetchAndJoin(): Promise<{ [id: number]: Character }> {
  const req1 = axios.get('/api/characters/summary');
  const users = await axios.get('/api/users');
  const usermap = {} as { [username: string]: string };
  for (const u of users.data) {
    usermap[u.dnd_beyond_name?.toLowerCase()] = u.display_name;
  }
  const resp = await req1;
  Object.keys(resp.data).forEach(function (key) {
    const ch = resp.data[key];
    resp.data[key].player_name =
      usermap[ch.dndbeyond_account?.toLowerCase()] || ch.dndbeyond_account;
  });
  return resp.data;
}
