function fn() {
  karate.configure('connectTimeout', 10000);
  karate.configure('readTimeout', 10000);
  return {
    baseUrl: 'http://api-test:8000',
    redisHost: 'redis-test'
  };
}
