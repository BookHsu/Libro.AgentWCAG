<template>
  <main>
    <button class="icon-only"></button>
    <a class="logo-link" href="/home"></a>
    <img class="hero" src="/hero.png" />
  </main>
</template>

<script setup>
import { ref } from 'vue'

// This string contains HTML-like content that must NOT be modified by auto-fix
const buttonTemplate = '<button class="dynamic">Click me</button>'
const imgTag = '<img src="/other.png" />'
const linkMarkup = '<a href="/target">Go</a>'

const count = ref(0)
function handleClick() {
  count.value++
}
</script>
