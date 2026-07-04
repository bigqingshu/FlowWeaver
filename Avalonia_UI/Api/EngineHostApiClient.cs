using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Models;

namespace Avalonia_UI.Api;

public sealed class EngineHostApiClient : IEngineHostApiClient
{
    private readonly HttpClient _httpClient;

    public EngineHostApiClient()
        : this(new HttpClient { Timeout = TimeSpan.FromSeconds(10) })
    {
    }

    public EngineHostApiClient(HttpClient httpClient)
    {
        _httpClient = httpClient;
    }

    public Task<ApiResponseEnvelope<HealthStatusDto>> GetHealthAsync(
        EngineHostConnectionSettings settings,
        CancellationToken cancellationToken = default)
    {
        return SendAsync<HealthStatusDto>(
            settings,
            HttpMethod.Get,
            "api/v1/health",
            authorize: false,
            cancellationToken: cancellationToken);
    }

    public Task<ApiResponseEnvelope<List<NodeDefinitionDto>>> ListNodeDefinitionsAsync(
        EngineHostConnectionSettings settings,
        CancellationToken cancellationToken = default)
    {
        return SendAsync<List<NodeDefinitionDto>>(
            settings,
            HttpMethod.Get,
            "api/v1/node-definitions",
            cancellationToken: cancellationToken);
    }

    public Task<ApiResponseEnvelope<List<WorkflowDefinitionDto>>> ListWorkflowsAsync(
        EngineHostConnectionSettings settings,
        CancellationToken cancellationToken = default)
    {
        return SendAsync<List<WorkflowDefinitionDto>>(
            settings,
            HttpMethod.Get,
            "api/v1/workflows",
            cancellationToken: cancellationToken);
    }

    public Task<ApiResponseEnvelope<WorkflowDefinitionDto>> CreateWorkflowAsync(
        EngineHostConnectionSettings settings,
        string name,
        JsonElement definition,
        CancellationToken cancellationToken = default)
    {
        return SendAsync<WorkflowDefinitionDto>(
            settings,
            HttpMethod.Post,
            "api/v1/workflows",
            payload: new WorkflowCreateRequestDto
            {
                Name = name,
                Definition = definition,
            },
            cancellationToken: cancellationToken);
    }

    public Task<ApiResponseEnvelope<WorkflowValidationResultDto>> ValidateWorkflowDraftAsync(
        EngineHostConnectionSettings settings,
        JsonElement definition,
        CancellationToken cancellationToken = default)
    {
        return SendAsync<WorkflowValidationResultDto>(
            settings,
            HttpMethod.Post,
            "api/v1/workflows/validate",
            payload: new WorkflowValidateRequestDto
            {
                Definition = definition,
            },
            cancellationToken: cancellationToken);
    }

    public Task<ApiResponseEnvelope<WorkflowDefinitionDto>> UpdateWorkflowAsync(
        EngineHostConnectionSettings settings,
        string workflowId,
        string? name,
        JsonElement definition,
        string baseRevisionId,
        CancellationToken cancellationToken = default)
    {
        return SendAsync<WorkflowDefinitionDto>(
            settings,
            HttpMethod.Put,
            $"api/v1/workflows/{Uri.EscapeDataString(workflowId)}",
            payload: new WorkflowUpdateRequestDto
            {
                Name = name,
                Definition = definition,
                BaseRevisionId = baseRevisionId,
            },
            cancellationToken: cancellationToken);
    }

    public Task<ApiResponseEnvelope<WorkflowDefinitionDto>> GetWorkflowAsync(
        EngineHostConnectionSettings settings,
        string workflowId,
        CancellationToken cancellationToken = default)
    {
        return SendAsync<WorkflowDefinitionDto>(
            settings,
            HttpMethod.Get,
            $"api/v1/workflows/{Uri.EscapeDataString(workflowId)}",
            cancellationToken: cancellationToken);
    }

    public Task<ApiResponseEnvelope<List<WorkflowRevisionDto>>> ListWorkflowRevisionsAsync(
        EngineHostConnectionSettings settings,
        string workflowId,
        CancellationToken cancellationToken = default)
    {
        return SendAsync<List<WorkflowRevisionDto>>(
            settings,
            HttpMethod.Get,
            $"api/v1/workflows/{Uri.EscapeDataString(workflowId)}/revisions",
            cancellationToken: cancellationToken);
    }

    public Task<ApiResponseEnvelope<WorkflowRevisionDto>> GetWorkflowRevisionAsync(
        EngineHostConnectionSettings settings,
        string workflowId,
        string revisionId,
        CancellationToken cancellationToken = default)
    {
        return SendAsync<WorkflowRevisionDto>(
            settings,
            HttpMethod.Get,
            $"api/v1/workflows/{Uri.EscapeDataString(workflowId)}/revisions/{Uri.EscapeDataString(revisionId)}",
            cancellationToken: cancellationToken);
    }

    public Task<ApiResponseEnvelope<WorkflowRunDto>> StartWorkflowRunAsync(
        EngineHostConnectionSettings settings,
        string workflowId,
        CancellationToken cancellationToken = default)
    {
        return SendAsync<WorkflowRunDto>(
            settings,
            HttpMethod.Post,
            $"api/v1/workflows/{Uri.EscapeDataString(workflowId)}/runs",
            cancellationToken: cancellationToken);
    }

    public Task<ApiResponseEnvelope<WorkflowRunDto>> StartWorkflowRunAsync(
        EngineHostConnectionSettings settings,
        string workflowId,
        string runMode,
        string? targetNodeInstanceId = null,
        CancellationToken cancellationToken = default)
    {
        var payload = new Dictionary<string, string?>
        {
            ["run_mode"] = runMode,
        };
        if (!string.IsNullOrWhiteSpace(targetNodeInstanceId))
        {
            payload["target_node_instance_id"] = targetNodeInstanceId;
        }

        return SendAsync<WorkflowRunDto>(
            settings,
            HttpMethod.Post,
            $"api/v1/workflows/{Uri.EscapeDataString(workflowId)}/runs",
            payload: payload,
            cancellationToken: cancellationToken);
    }

    public Task<ApiResponseEnvelope<List<WorkflowRunDto>>> ListRunsAsync(
        EngineHostConnectionSettings settings,
        string? workflowId = null,
        IReadOnlyCollection<string>? statuses = null,
        CancellationToken cancellationToken = default)
    {
        var query = new List<KeyValuePair<string, string?>>();
        if (!string.IsNullOrWhiteSpace(workflowId))
        {
            query.Add(new KeyValuePair<string, string?>("workflow_id", workflowId));
        }

        if (statuses is not null)
        {
            query.AddRange(statuses.Select(status => new KeyValuePair<string, string?>("status", status)));
        }

        return SendAsync<List<WorkflowRunDto>>(
            settings,
            HttpMethod.Get,
            "api/v1/runs",
            query: query,
            cancellationToken: cancellationToken);
    }

    public Task<ApiResponseEnvelope<List<NodeRunDto>>> ListNodeRunsAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        CancellationToken cancellationToken = default)
    {
        return SendAsync<List<NodeRunDto>>(
            settings,
            HttpMethod.Get,
            $"api/v1/runs/{Uri.EscapeDataString(workflowRunId)}/nodes",
            cancellationToken: cancellationToken);
    }

    public Task<ApiResponseEnvelope<WorkflowProcessDto>> CancelRunAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        CancellationToken cancellationToken = default)
    {
        return SendAsync<WorkflowProcessDto>(
            settings,
            HttpMethod.Post,
            $"api/v1/runs/{Uri.EscapeDataString(workflowRunId)}/cancel",
            cancellationToken: cancellationToken);
    }

    public Task<ApiResponseEnvelope<List<TableRefDto>>> ListTableRefsAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        CancellationToken cancellationToken = default)
    {
        return SendAsync<List<TableRefDto>>(
            settings,
            HttpMethod.Get,
            $"api/v1/runs/{Uri.EscapeDataString(workflowRunId)}/table-refs",
            cancellationToken: cancellationToken);
    }

    public Task<ApiResponseEnvelope<TableDataSchemaDto>> GetTableDataSchemaAsync(
        EngineHostConnectionSettings settings,
        string tableRefId,
        CancellationToken cancellationToken = default)
    {
        return SendAsync<TableDataSchemaDto>(
            settings,
            HttpMethod.Get,
            $"api/v1/data/{Uri.EscapeDataString(tableRefId)}/schema",
            cancellationToken: cancellationToken);
    }

    public Task<ApiResponseEnvelope<TableDataSummaryDto>> GetTableDataSummaryAsync(
        EngineHostConnectionSettings settings,
        string tableRefId,
        CancellationToken cancellationToken = default)
    {
        return SendAsync<TableDataSummaryDto>(
            settings,
            HttpMethod.Get,
            $"api/v1/data/{Uri.EscapeDataString(tableRefId)}/summary",
            cancellationToken: cancellationToken);
    }

    public Task<ApiResponseEnvelope<TableDataRowsDto>> GetTableDataRowsAsync(
        EngineHostConnectionSettings settings,
        string tableRefId,
        int offset = 0,
        int limit = 50,
        IReadOnlyCollection<string>? columns = null,
        IReadOnlyCollection<string>? orderBy = null,
        CancellationToken cancellationToken = default)
    {
        var query = new List<KeyValuePair<string, string?>>
        {
            new("offset", offset.ToString()),
            new("limit", limit.ToString()),
        };
        if (columns is not null)
        {
            query.AddRange(columns.Select(column => new KeyValuePair<string, string?>("columns", column)));
        }

        if (orderBy is not null)
        {
            query.AddRange(orderBy.Select(column => new KeyValuePair<string, string?>("order_by", column)));
        }

        return SendAsync<TableDataRowsDto>(
            settings,
            HttpMethod.Get,
            $"api/v1/data/{Uri.EscapeDataString(tableRefId)}/rows",
            query: query,
            cancellationToken: cancellationToken);
    }

    public Task<ApiResponseEnvelope<List<RuntimeEventDto>>> ListEventsAsync(
        EngineHostConnectionSettings settings,
        long? afterSequenceNumber = null,
        string? workflowRunId = null,
        string? nodeRunId = null,
        string? eventType = null,
        int limit = 100,
        CancellationToken cancellationToken = default)
    {
        var query = new List<KeyValuePair<string, string?>>
        {
            new("after_sequence_number", afterSequenceNumber?.ToString()),
            new("workflow_run_id", workflowRunId),
            new("node_run_id", nodeRunId),
            new("event_type", eventType),
            new("limit", limit.ToString()),
        };

        return SendAsync<List<RuntimeEventDto>>(
            settings,
            HttpMethod.Get,
            "api/v1/events",
            query: query,
            cancellationToken: cancellationToken);
    }

    public Task<ApiResponseEnvelope<List<AuditEventDto>>> ListAuditEventsAsync(
        EngineHostConnectionSettings settings,
        string? workflowRunId = null,
        string? nodeRunId = null,
        string? eventType = null,
        CancellationToken cancellationToken = default)
    {
        var query = new List<KeyValuePair<string, string?>>
        {
            new("workflow_run_id", workflowRunId),
            new("node_run_id", nodeRunId),
            new("event_type", eventType),
        };

        return SendAsync<List<AuditEventDto>>(
            settings,
            HttpMethod.Get,
            "api/v1/audit-events",
            query: query,
            cancellationToken: cancellationToken);
    }

    public Task<ApiResponseEnvelope<List<SharedPublicationDto>>> ListSharedPublicationsAsync(
        EngineHostConnectionSettings settings,
        string? shareName = null,
        int limit = 100,
        CancellationToken cancellationToken = default)
    {
        var query = new List<KeyValuePair<string, string?>>
        {
            new("share_name", shareName),
            new("limit", limit.ToString()),
        };

        return SendAsync<List<SharedPublicationDto>>(
            settings,
            HttpMethod.Get,
            "api/v1/shared-publications",
            query: query,
            cancellationToken: cancellationToken);
    }

    public Task<ApiResponseEnvelope<List<SharedPublicationDto>>> ListSharedPublicationVersionsAsync(
        EngineHostConnectionSettings settings,
        string shareName,
        int limit = 100,
        CancellationToken cancellationToken = default)
    {
        var query = new List<KeyValuePair<string, string?>>
        {
            new("limit", limit.ToString()),
        };

        return SendAsync<List<SharedPublicationDto>>(
            settings,
            HttpMethod.Get,
            $"api/v1/shared-publications/{Uri.EscapeDataString(shareName)}/versions",
            query: query,
            cancellationToken: cancellationToken);
    }

    public async Task<ApiResponseEnvelope<TData>> SendAsync<TData>(
        EngineHostConnectionSettings settings,
        HttpMethod method,
        string path,
        IEnumerable<KeyValuePair<string, string?>>? query = null,
        object? payload = null,
        bool authorize = true,
        CancellationToken cancellationToken = default)
    {
        if (authorize && string.IsNullOrWhiteSpace(settings.Token))
        {
            return ApiResponseEnvelope<TData>.Failure(
                "TOKEN_REQUIRED",
                "EngineHost token is required.");
        }

        Uri requestUri;
        try
        {
            requestUri = settings.BuildApiUri(path, query);
        }
        catch (InvalidOperationException ex)
        {
            return ApiResponseEnvelope<TData>.Failure("INVALID_BASE_URL", ex.Message);
        }

        using var request = new HttpRequestMessage(method, requestUri);
        if (authorize)
        {
            request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", settings.Token);
        }

        if (payload is not null)
        {
            var json = JsonSerializer.Serialize(payload, FlowWeaverJson.Options);
            request.Content = new StringContent(json, Encoding.UTF8, "application/json");
        }

        HttpResponseMessage response;
        string body;
        try
        {
            response = await _httpClient.SendAsync(
                request,
                HttpCompletionOption.ResponseHeadersRead,
                cancellationToken);
            using (response)
            {
                body = await response.Content.ReadAsStringAsync(cancellationToken);

                if (TryDeserializeEnvelope<TData>(body, out var envelope))
                {
                    return envelope;
                }

                return ApiResponseEnvelope<TData>.Failure(
                    "INVALID_RESPONSE",
                    response.IsSuccessStatusCode
                        ? "EngineHost response was not a valid API envelope."
                        : $"EngineHost returned {(int)response.StatusCode} {response.ReasonPhrase}.");
            }
        }
        catch (TaskCanceledException) when (!cancellationToken.IsCancellationRequested)
        {
            return ApiResponseEnvelope<TData>.Failure(
                "REQUEST_TIMEOUT",
                "EngineHost request timed out.",
                retryable: true);
        }
        catch (HttpRequestException ex)
        {
            return ApiResponseEnvelope<TData>.Failure(
                "REQUEST_FAILED",
                ex.Message,
                retryable: true);
        }
    }

    private static bool TryDeserializeEnvelope<TData>(
        string body,
        out ApiResponseEnvelope<TData> envelope)
    {
        try
        {
            var parsed = JsonSerializer.Deserialize<ApiResponseEnvelope<TData>>(
                body,
                FlowWeaverJson.Options);
            if (parsed is not null)
            {
                envelope = parsed;
                return true;
            }
        }
        catch (JsonException)
        {
        }

        envelope = ApiResponseEnvelope<TData>.Failure(
            "INVALID_RESPONSE",
            "EngineHost response was not valid JSON.");
        return false;
    }
}
