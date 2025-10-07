#!/usr/bin/env ruby
# frozen_string_literal: true

require 'yaml'
require 'json'
require 'time'

workflow_path = File.expand_path('../.github/workflows/mirror-iRingo.yml', __dir__)
workflow = YAML.safe_load(File.read(workflow_path), aliases: true)

raise 'Expected jobs.download_assets.steps to be an Array' unless workflow.dig('jobs', 'download_assets', 'steps').is_a?(Array)

required_step_names = [
  'Checkout main branch',
  'Set repository list',
  'Download and categorize release assets'
]

step_names = workflow.dig('jobs', 'download_assets', 'steps').map { |step| step['name'] }.compact

missing_steps = required_step_names - step_names

unless missing_steps.empty?
  warn "Missing expected steps: #{missing_steps.join(', ')}"
  exit 1
end

puts({
  workflow: File.basename(workflow_path),
  steps: step_names,
  validated_at: Time.now.utc.iso8601
}.to_json)
