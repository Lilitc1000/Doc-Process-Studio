<template>
  <router-view v-slot="{ Component, route }">
    <Transition name="page-switch" mode="out-in">
      <component :is="Component" :key="route.path" />
    </Transition>
  </router-view>
</template>

<script setup lang="ts"></script>
