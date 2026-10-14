<template>
  <div>欢迎你: {{ userInfo?.name }}</div>
</template>

<script setup>
import { useUser } from '@/utils/user'

const { userInfo } = useUser()
</script>
