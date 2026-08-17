Feature: Jobs API against real Postgres and Redis

  Background:
    # Karate scenarios are independent, so each scenario starts from a clean
    # slate: truncate the jobs table and flush the queue. This keeps the
    # assertions deterministic even across re-runs against reused containers.
    * def DbUtils = Java.type('karatehelpers.DbUtils')
    * def truncated = DbUtils.execute('TRUNCATE jobs')
    * def Jedis = Java.type('redis.clients.jedis.Jedis')
    * def jedis = new Jedis(redisHost, 6379, 5000)
    * def flushed = jedis.flushAll()
    * def closed = jedis.close()

  Scenario: create an adHoc job and verify the Postgres row and Redis queue membership
    * def payload = { repo: 'example/foobar', type: 'adHoc', prompt: 'Write a hello world script', model: 'deepseek/deepseek-v4-flash' }
    Given url baseUrl
    And path 'jobs'
    And request payload
    When method post
    Then status 200
    And match response.status == 'queued'
    And def jobId = response.job_id
    And match jobId == '#uuid'

    # Row-level assertion against the real Postgres instance.
    * def rows = DbUtils.query("select id, prompt, issue_number, repo, model, type, status from jobs where id = '" + jobId + "'")
    * match rows == '#[1]'
    * match rows[0].id == jobId
    * match rows[0].status == 'queued'
    * match rows[0].repo == 'example/foobar'
    * match rows[0].prompt == 'Write a hello world script'
    * match rows[0].model == 'deepseek/deepseek-v4-flash'
    * match rows[0].type == 'adHoc'
    * match rows[0].issue_number == null

    # GET round-trip of the same row through the API.
    Given url baseUrl
    And path 'jobs', jobId
    When method get
    Then status 200
    And match response.id == jobId
    And match response.status == 'queued'
    And match response.repo == 'example/foobar'
    And match response.prompt == 'Write a hello world script'
    And match response.model == 'deepseek/deepseek-v4-flash'
    And match response.type == 'adHoc'
    And match response.issue_number == null

    # Direct queue-membership check against the real Redis instance.
    * def Jedis = Java.type('redis.clients.jedis.Jedis')
    * def jedis = new Jedis(redisHost, 6379, 5000)
    * def queue = jedis.lrange('jobs', 0, -1)
    * match queue contains jobId
    * def closed = jedis.close()

  Scenario: create an issueResolver job and verify the Postgres row and Redis queue membership
    * def payload = { repo: 'example/foobar', type: 'issueResolver', issueNumber: 42 }
    Given url baseUrl
    And path 'jobs'
    And request payload
    When method post
    Then status 200
    And match response.status == 'queued'
    And def jobId = response.job_id
    And match jobId == '#uuid'

    * def rows = DbUtils.query("select id, prompt, issue_number, repo, model, type, status from jobs where id = '" + jobId + "'")
    * match rows == '#[1]'
    * match rows[0].id == jobId
    * match rows[0].status == 'queued'
    * match rows[0].repo == 'example/foobar'
    * match rows[0].issue_number == 42
    * match rows[0].prompt == null
    * match rows[0].model == null
    * match rows[0].type == 'issueResolver'

    Given url baseUrl
    And path 'jobs', jobId
    When method get
    Then status 200
    And match response.id == jobId
    And match response.status == 'queued'
    And match response.repo == 'example/foobar'
    And match response.issue_number == 42
    And match response.prompt == null
    And match response.type == 'issueResolver'

    * def Jedis = Java.type('redis.clients.jedis.Jedis')
    * def jedis = new Jedis(redisHost, 6379, 5000)
    * def queue = jedis.lrange('jobs', 0, -1)
    * match queue contains jobId
    * def closed = jedis.close()

  Scenario: create an issueArchitect job and verify the Postgres row and Redis queue membership
    * def payload = { repo: 'example/foobar', issueNumber: 42, type: 'issueArchitect' }
    Given url baseUrl
    And path 'jobs'
    And request payload
    When method post
    Then status 200
    And match response.status == 'queued'
    And def jobId = response.job_id
    And match jobId == '#uuid'

    * def rows = DbUtils.query("select id, prompt, issue_number, repo, model, type, status from jobs where id = '" + jobId + "'")
    * match rows == '#[1]'
    * match rows[0].id == jobId
    * match rows[0].status == 'queued'
    * match rows[0].repo == 'example/foobar'
    * match rows[0].issue_number == 42
    * match rows[0].prompt == null
    * match rows[0].model == null
    * match rows[0].type == 'issueArchitect'

    Given url baseUrl
    And path 'jobs', jobId
    When method get
    Then status 200
    And match response.id == jobId
    And match response.status == 'queued'
    And match response.repo == 'example/foobar'
    And match response.issue_number == 42
    And match response.prompt == null
    And match response.type == 'issueArchitect'

    * def Jedis = Java.type('redis.clients.jedis.Jedis')
    * def jedis = new Jedis(redisHost, 6379, 5000)
    * def queue = jedis.lrange('jobs', 0, -1)
    * match queue contains jobId
    * def closed = jedis.close()

  Scenario: create an adHoc job with an explicit custom model and verify the row and queue
    * def payload = { repo: 'example/foobar', type: 'adHoc', prompt: 'Write a poem', model: 'deepseek/deepseek-v4-pro' }
    Given url baseUrl
    And path 'jobs'
    And request payload
    When method post
    Then status 200
    And match response.status == 'queued'
    And def jobId = response.job_id

    * def rows = DbUtils.query("select id, prompt, issue_number, repo, model, type, status from jobs where id = '" + jobId + "'")
    * match rows == '#[1]'
    * match rows[0].repo == 'example/foobar'
    * match rows[0].prompt == 'Write a poem'
    * match rows[0].model == 'deepseek/deepseek-v4-pro'
    * match rows[0].type == 'adHoc'
    * match rows[0].issue_number == null

    Given url baseUrl
    And path 'jobs', jobId
    When method get
    Then status 200
    And match response.id == jobId
    And match response.model == 'deepseek/deepseek-v4-pro'

    * def Jedis = Java.type('redis.clients.jedis.Jedis')
    * def jedis = new Jedis(redisHost, 6379, 5000)
    * def queue = jedis.lrange('jobs', 0, -1)
    * match queue contains jobId
    * def closed = jedis.close()

  Scenario: GET a job that does not exist returns an error
    Given url baseUrl
    And path 'jobs', '00000000-0000-0000-0000-000000000000'
    When method get
    Then status 200
    And match response == { error: 'not found' }

  Scenario: invalid requests are rejected with 400 and write nothing to Postgres or Redis
    * def rowCountBefore = DbUtils.queryValue('select count(*) from jobs')
    * def Jedis = Java.type('redis.clients.jedis.Jedis')
    * def jedis = new Jedis(redisHost, 6379, 5000)
    * def queueBefore = jedis.lrange('jobs', 0, -1).size()
    * def closed = jedis.close()

    # Missing repo.
    Given url baseUrl
    And path 'jobs'
    And request { type: 'adHoc', prompt: 'hello' }
    When method post
    Then status 400

    # Missing type.
    Given url baseUrl
    And path 'jobs'
    And request { repo: 'example/foobar' }
    When method post
    Then status 400

    # A type is present but its required field is missing.
    Given url baseUrl
    And path 'jobs'
    And request { repo: 'example/foobar', type: 'issueResolver' }
    When method post
    Then status 400

    # Malformed model (not provider/model).
    Given url baseUrl
    And path 'jobs'
    And request { repo: 'example/foobar', type: 'adHoc', prompt: 'hello', model: 'not-a-model' }
    When method post
    Then status 400

    # issueNumber must be positive.
    Given url baseUrl
    And path 'jobs'
    And request { repo: 'example/foobar', type: 'issueResolver', issueNumber: 0 }
    When method post
    Then status 400

    # An adHoc prompt cannot be combined with an issueNumber.
    Given url baseUrl
    And path 'jobs'
    And request { repo: 'example/foobar', type: 'adHoc', prompt: 'hello', issueNumber: 42 }
    When method post
    Then status 400

    # Nothing was inserted into Postgres and nothing was enqueued in Redis.
    * def rowCountAfter = DbUtils.queryValue('select count(*) from jobs')
    * match rowCountAfter == rowCountBefore
    * def Jedis = Java.type('redis.clients.jedis.Jedis')
    * def jedis = new Jedis(redisHost, 6379, 5000)
    * def queueAfter = jedis.lrange('jobs', 0, -1).size()
    * match queueAfter == queueBefore
    * def closed = jedis.close()
