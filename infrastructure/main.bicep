@description('Location for all resources')
param location string = resourceGroup().location

@description('Container App Environment name')
param environmentName string = 'env-agentic-team'

@description('Container App name')
param containerAppName string = 'app-agentic-orchestrator'

@description('Container image')
param containerImage string

@description('Azure OpenAI API Key')
@secure()
param azureOpenAIKey string

@description('Azure OpenAI Endpoint')
param azureOpenAIEndpoint string

// Container Apps Environment
resource environment 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: environmentName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
    }
  }
}

// Container App
resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: containerAppName
  location: location
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false
      }
      secrets: [
        {
          name: 'azure-openai-key'
          value: azureOpenAIKey
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'orchestrator'
          image: containerImage
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            {
              name: 'AZURE_OPENAI_KEY'
              secretRef: 'azure-openai-key'
            }
            {
              name: 'AZURE_OPENAI_ENDPOINT'
              value: azureOpenAIEndpoint
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 5
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '10'
              }
            }
          }
        ]
      }
    }
  }
}

output fqdn string = containerApp.properties.configuration.ingress.fqdn
