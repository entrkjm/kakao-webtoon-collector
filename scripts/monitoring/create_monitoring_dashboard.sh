#!/bin/bash
# Cloud Monitoring 대시보드 생성 스크립트

set -e

PROJECT_ID="${GCP_PROJECT_ID:-kakao-webtoon-collector}"
REGION="${GCP_REGION:-asia-northeast3}"
SERVICE_NAME="pipeline-function"
SCHEDULER_JOB_ID="kakao-webtoon-weekly-collection"
DASHBOARD_NAME="kakao-webtoon-pipeline"

echo "=== Cloud Monitoring 대시보드 생성 ==="
echo "프로젝트: $PROJECT_ID"
echo "대시보드명: $DASHBOARD_NAME"
echo ""

# 대시보드 JSON 정의 (Cloud Run Revision 기반)
DASHBOARD_JSON=$(cat <<EOF
{
  "displayName": "$DASHBOARD_NAME",
  "mosaicLayout": {
    "columns": 12,
    "tiles": [
      {
        "width": 6,
        "height": 4,
        "xPos": 0,
        "yPos": 0,
        "widget": {
          "title": "Pipeline Function 실행 횟수",
          "xyChart": {
            "dataSets": [
              {
                "timeSeriesQuery": {
                  "timeSeriesFilter": {
                    "filter": "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"$SERVICE_NAME\" AND metric.type=\"run.googleapis.com/request_count\"",
                    "aggregation": {
                      "perSeriesAligner": "ALIGN_RATE",
                      "crossSeriesReducer": "REDUCE_SUM",
                      "alignmentPeriod": "60s"
                    }
                  }
                },
                "plotType": "LINE"
              }
            ],
            "timeshiftDuration": "0s",
            "yAxis": {
              "label": "y1Axis",
              "scale": "LINEAR"
            }
          }
        }
      },
      {
        "width": 6,
        "height": 4,
        "xPos": 6,
        "yPos": 0,
        "widget": {
          "title": "Pipeline Function 실행 시간",
          "xyChart": {
            "dataSets": [
              {
                "timeSeriesQuery": {
                  "timeSeriesFilter": {
                    "filter": "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"$SERVICE_NAME\" AND metric.type=\"run.googleapis.com/request_latencies\"",
                    "aggregation": {
                      "perSeriesAligner": "ALIGN_MEAN",
                      "crossSeriesReducer": "REDUCE_MEAN",
                      "alignmentPeriod": "60s"
                    }
                  }
                },
                "plotType": "LINE"
              }
            ],
            "timeshiftDuration": "0s",
            "yAxis": {
              "label": "y1Axis",
              "scale": "LINEAR"
            }
          }
        }
      },
      {
        "width": 6,
        "height": 4,
        "xPos": 0,
        "yPos": 4,
        "widget": {
          "title": "Pipeline Function 에러 발생 횟수",
          "xyChart": {
            "dataSets": [
              {
                "timeSeriesQuery": {
                  "timeSeriesFilter": {
                    "filter": "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"$SERVICE_NAME\" AND metric.type=\"run.googleapis.com/request_count\" AND metric.labels.response_code >= \"400\"",
                    "aggregation": {
                      "perSeriesAligner": "ALIGN_RATE",
                      "crossSeriesReducer": "REDUCE_SUM",
                      "alignmentPeriod": "60s"
                    }
                  }
                },
                "plotType": "LINE"
              }
            ],
            "timeshiftDuration": "0s",
            "yAxis": {
              "label": "y1Axis",
              "scale": "LINEAR"
            }
          }
        }
      },
      {
        "width": 6,
        "height": 4,
        "xPos": 6,
        "yPos": 4,
        "widget": {
          "title": "Cloud Scheduler 작업 실행 횟수",
          "xyChart": {
            "dataSets": [
              {
                "timeSeriesQuery": {
                  "timeSeriesFilter": {
                    "filter": "resource.type=\"cloud_scheduler_job\" AND resource.labels.job_id=\"$SCHEDULER_JOB_ID\"",
                    "metric": {
                      "type": "cloudscheduler.googleapis.com/job/execution_count"
                    },
                    "aggregation": {
                      "perSeriesAligner": "ALIGN_RATE",
                      "crossSeriesReducer": "REDUCE_SUM",
                      "alignmentPeriod": "60s"
                    }
                  }
                },
                "plotType": "LINE"
              }
            ],
            "timeshiftDuration": "0s",
            "yAxis": {
              "label": "y1Axis",
              "scale": "LINEAR"
            }
          }
        }
      }
    ]
  }
}
EOF
)

# 임시 파일에 대시보드 JSON 저장
TEMP_FILE=$(mktemp)
echo "$DASHBOARD_JSON" > "$TEMP_FILE"

echo "대시보드 생성 중..."
gcloud monitoring dashboards create \
  --config-from-file="$TEMP_FILE" \
  --project="$PROJECT_ID" 2>&1 | grep -v "Waiting on" || {
    echo "⚠️  대시보드 생성 실패 (이미 존재할 수 있음)"
    echo "기존 대시보드를 업데이트하려면 Cloud Console에서 수동으로 수정하세요."
    echo ""
    echo "대시보드 확인:"
    echo "  https://console.cloud.google.com/monitoring/dashboards?project=$PROJECT_ID"
    rm "$TEMP_FILE"
    exit 0
}

rm "$TEMP_FILE"

echo ""
echo "✅ 대시보드 생성 완료!"
echo ""
echo "대시보드 확인:"
echo "  https://console.cloud.google.com/monitoring/dashboards?project=$PROJECT_ID"

