{{/*
Expand the name of the chart.
*/}}
{{- define "rag-stack.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "rag-stack.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "rag-stack.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "rag-stack.labels" -}}
helm.sh/chart: {{ include "rag-stack.chart" . }}
{{ include "rag-stack.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "rag-stack.selectorLabels" -}}
app.kubernetes.io/name: {{ include "rag-stack.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "rag-stack.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "rag-stack.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Backend fullname
*/}}
{{- define "rag-stack.backend.fullname" -}}
{{- printf "%s-backend" (include "rag-stack.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Frontend fullname
*/}}
{{- define "rag-stack.frontend.fullname" -}}
{{- printf "%s-frontend" (include "rag-stack.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
PostgreSQL fullname
*/}}
{{- define "rag-stack.postgresql.fullname" -}}
{{- printf "%s-postgresql" (include "rag-stack.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Database URL for backend
*/}}
{{- define "rag-stack.databaseUrl" -}}
{{- printf "postgresql+asyncpg://postgres:%s@%s:5432/%s" .Values.postgresql.auth.postgresPassword (include "rag-stack.postgresql.fullname" .) .Values.postgresql.auth.database }}
{{- end }}
