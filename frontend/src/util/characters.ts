import axios from 'axios';

export type Character = {
	id: number;
	name: string;
	dndbeyond_account: string;
	campaign: string;
	character_sheet: string;
	avatar: string;
	race: string;
	base_race: string;
	class_description: string;
	classes: {[class_: string]: number};
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

let cache = null as null | {[id: number]: Character};

export async function fetchCharacterData(): Promise<{[id: number]: Character}> {
	if(cache !== null) {
		return new Promise(resolve => resolve(cache!));
	}
	const resp = await axios.get('/api/characters/summary');
	cache = resp.data;
	return resp.data;
}
