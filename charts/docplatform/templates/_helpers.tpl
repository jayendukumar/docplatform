{{- define "docplatform.name" -}}
docplatform
{{- end }}

{{- define "docplatform.labels" -}}
app.kubernetes.io/name: {{ include "docplatform.name" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}
