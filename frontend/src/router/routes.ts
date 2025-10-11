import { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('layouts/MainLayout.vue'),
    children: [
      { path: '', component: () => import('pages/IndexPage.vue') },
      // TODO: Put the date in the URL
      { path: 'profile', component: () => import('pages/ProfilePage.vue') },
      { path: 'signups', component: () => import('pages/SignupsPage.vue') },
      {
        path: 'characters',
        component: () => import('pages/CharactersPage.vue'),
        props: true,
      },
      {
        name: 'character',
        path: 'characters/:id',
        component: () => import('pages/CharacterPage.vue'),
        props: true,
      },
      {
        name: 'playerCharacter',
        path: 'pc/:id',
        component: () => import('pages/FindCharacterPage.vue'),
        props: true,
      },
    ],
  },

  // Always leave this as last one,
  // but you can also remove it
  {
    path: '/:catchAll(.*)*',
    component: () => import('pages/ErrorNotFound.vue'),
  },
];

export default routes;
