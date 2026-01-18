from datadog import initialize, statsd

options = {
    'statsd_host': '127.0.0.1',
    'statsd_port': 8125
}
initialize(**options)

statsd.gauge('forwardog.dogstatsd.gauge2', 42, tags=['env:test', 'source:forwardog'])
