Feature: Health endpoint

Scenario: GET /health reports the real dependencies
  Given url baseUrl
  And path 'health'
  When method get
  Then status 200
  And match response.postgres == 'configured'
  # A real ping against the throwaway Redis instance.
  And match response.redis == true
