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

    public Task<ApiResponseEnvelope<NodeDefinitionCatalogStateDto>> GetNodeDefinitionCatalogStateAsync(
        EngineHostConnectionSettings settings,
        CancellationToken cancellationToken = default)
    {
        return SendAsync<NodeDefinitionCatalogStateDto>(
            settings,
            HttpMethod.Get,
            "api/v1/node-definitions/state",
            cancellationToken: cancellationToken);
    }

    public Task<ApiResponseEnvelope<SqliteTableCatalogDto>> ListSqliteTablesAsync(
        EngineHostConnectionSettings settings,
        string databasePath,
        CancellationToken cancellationToken = default)
    {
        return SendAsync<SqliteTableCatalogDto>(
            settings,
            HttpMethod.Post,
            "api/v1/node-resources/sqlite/tables",
            payload: new SqliteTableCatalogRequestDto
            {
                DatabasePath = databasePath,
            },
            cancellationToken: cancellationToken);
    }

    public Task<ApiResponseEnvelope<List<PluginCatalogEntryDto>>> ListPluginsAsync(
        EngineHostConnectionSettings settings,
        CancellationToken cancellationToken = default)
    {
        return SendAsync<List<PluginCatalogEntryDto>>(
            settings,
            HttpMethod.Get,
            "api/v1/plugins",
            cancellationToken: cancellationToken);
    }

    public Task<ApiResponseEnvelope<PluginCatalogStateDto>> GetPluginCatalogStateAsync(
        EngineHostConnectionSettings settings,
        CancellationToken cancellationToken = default)
    {
        return SendAsync<PluginCatalogStateDto>(
            settings,
            HttpMethod.Get,
            "api/v1/plugins/state",
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

    public Task<ApiResponseEnvelope<WorkflowDeleteResultDto>> DeleteWorkflowAsync(
        EngineHostConnectionSettings settings,
        string workflowId,
        CancellationToken cancellationToken = default)
    {
        return SendAsync<WorkflowDeleteResultDto>(
            settings,
            HttpMethod.Delete,
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

    public Task<ApiResponseEnvelope<WorkflowRunDto>> StartBackgroundWorkflowRunAsync(
        EngineHostConnectionSettings settings,
        string workflowId,
        string runMode = "full",
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
            $"api/v1/workflows/{Uri.EscapeDataString(workflowId)}/background-runs",
            payload: payload,
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

    public Task<ApiResponseEnvelope<List<WorkflowRunDto>>> ListRunsPageAsync(
        EngineHostConnectionSettings settings,
        string? workflowId = null,
        IReadOnlyCollection<string>? statuses = null,
        string? runMode = null,
        string? triggerSource = null,
        int offset = 0,
        int limit = 100,
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

        if (!string.IsNullOrWhiteSpace(runMode))
        {
            query.Add(new KeyValuePair<string, string?>("run_mode", runMode));
        }

        if (!string.IsNullOrWhiteSpace(triggerSource))
        {
            query.Add(new KeyValuePair<string, string?>("trigger_source", triggerSource));
        }

        query.Add(new KeyValuePair<string, string?>("offset", offset.ToString()));
        query.Add(new KeyValuePair<string, string?>("limit", limit.ToString()));

        return SendAsync<List<WorkflowRunDto>>(
            settings,
            HttpMethod.Get,
            "api/v1/runs",
            query: query,
            cancellationToken: cancellationToken);
    }

    public Task<ApiResponseEnvelope<WorkflowRunDto>> GetRunAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        CancellationToken cancellationToken = default)
    {
        return SendAsync<WorkflowRunDto>(
            settings,
            HttpMethod.Get,
            $"api/v1/runs/{Uri.EscapeDataString(workflowRunId)}",
            cancellationToken: cancellationToken);
    }

    public Task<ApiResponseEnvelope<WorkflowRunDeleteResultDto>> DeleteRunAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        CancellationToken cancellationToken = default)
    {
        return SendAsync<WorkflowRunDeleteResultDto>(
            settings,
            HttpMethod.Delete,
            $"api/v1/runs/{Uri.EscapeDataString(workflowRunId)}",
            cancellationToken: cancellationToken);
    }

    public Task<ApiResponseEnvelope<RunReviewDto>> GetRunReviewAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        CancellationToken cancellationToken = default)
    {
        return SendAsync<RunReviewDto>(
            settings,
            HttpMethod.Get,
            $"api/v1/runs/{Uri.EscapeDataString(workflowRunId)}/review",
            cancellationToken: cancellationToken);
    }

    public Task<ApiResponseEnvelope<WorkflowRunRuntimeOptionsDto>> GetRunRuntimeOptionsAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        CancellationToken cancellationToken = default)
    {
        return SendAsync<WorkflowRunRuntimeOptionsDto>(
            settings,
            HttpMethod.Get,
            $"api/v1/runs/{Uri.EscapeDataString(workflowRunId)}/runtime-options",
            cancellationToken: cancellationToken);
    }

    public Task<ApiResponseEnvelope<WorkflowRunRuntimeOptionsDto>> ReplaceRunRuntimeOptionsAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        int expectedVersion,
        WorkflowRunRuntimeOptionsOverlayDto overlay,
        CancellationToken cancellationToken = default)
    {
        return SendAsync<WorkflowRunRuntimeOptionsDto>(
            settings,
            HttpMethod.Put,
            $"api/v1/runs/{Uri.EscapeDataString(workflowRunId)}/runtime-options",
            payload: new WorkflowRunRuntimeOptionsUpdateRequestDto
            {
                ExpectedVersion = expectedVersion,
                Overlay = overlay,
            },
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

    public Task<ApiResponseEnvelope<NodeRunPageDto>> ListNodeRunsPageAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        int offset = 0,
        int limit = 100,
        IReadOnlyCollection<string>? statuses = null,
        CancellationToken cancellationToken = default)
    {
        var query = new List<KeyValuePair<string, string?>>
        {
            new("paged", "true"),
            new("offset", offset.ToString()),
            new("limit", limit.ToString()),
        };
        if (statuses is not null)
        {
            query.AddRange(statuses.Select(status => new KeyValuePair<string, string?>("status", status)));
        }

        return SendAsync<NodeRunPageDto>(
            settings,
            HttpMethod.Get,
            $"api/v1/runs/{Uri.EscapeDataString(workflowRunId)}/nodes",
            query: query,
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

    public Task<ApiResponseEnvelope<TableRefDto>> GetTableRefAsync(
        EngineHostConnectionSettings settings,
        string tableRefId,
        CancellationToken cancellationToken = default)
    {
        return SendAsync<TableRefDto>(
            settings,
            HttpMethod.Get,
            $"api/v1/data/{Uri.EscapeDataString(tableRefId)}",
            cancellationToken: cancellationToken);
    }

    public Task<ApiResponseEnvelope<RunTableDirectoryPageDto>> ListRunTableDirectoryAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        int offset = 0,
        int limit = 100,
        string? nodeRunId = null,
        string? tableType = null,
        IReadOnlyCollection<string>? lifecycleStatuses = null,
        string? logicalTableId = null,
        CancellationToken cancellationToken = default)
    {
        var query = new List<KeyValuePair<string, string?>>
        {
            new("paged", "true"),
            new("offset", offset.ToString()),
            new("limit", limit.ToString()),
        };
        if (!string.IsNullOrWhiteSpace(nodeRunId))
        {
            query.Add(new KeyValuePair<string, string?>("node_run_id", nodeRunId));
        }

        if (!string.IsNullOrWhiteSpace(tableType))
        {
            query.Add(new KeyValuePair<string, string?>("table_type", tableType));
        }

        if (lifecycleStatuses is not null)
        {
            query.AddRange(lifecycleStatuses.Select(
                status => new KeyValuePair<string, string?>("lifecycle", status)));
        }

        if (!string.IsNullOrWhiteSpace(logicalTableId))
        {
            query.Add(new KeyValuePair<string, string?>("logical_table_id", logicalTableId));
        }

        return SendAsync<RunTableDirectoryPageDto>(
            settings,
            HttpMethod.Get,
            $"api/v1/runs/{Uri.EscapeDataString(workflowRunId)}/table-refs",
            query: query,
            cancellationToken: cancellationToken);
    }

    public Task<ApiResponseEnvelope<List<LoopRunDto>>> ListLoopRunsAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        int offset = 0,
        int limit = 50,
        IReadOnlyCollection<string>? statuses = null,
        CancellationToken cancellationToken = default)
    {
        var query = BuildPagedStatusQuery(offset, limit, statuses);
        return SendAsync<List<LoopRunDto>>(
            settings,
            HttpMethod.Get,
            $"api/v1/runs/{Uri.EscapeDataString(workflowRunId)}/loops",
            query: query,
            cancellationToken: cancellationToken);
    }

    public Task<ApiResponseEnvelope<List<LoopIterationRunDto>>> ListLoopIterationsAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        string loopRunId,
        int offset = 0,
        int limit = 50,
        IReadOnlyCollection<string>? statuses = null,
        CancellationToken cancellationToken = default)
    {
        var query = BuildPagedStatusQuery(offset, limit, statuses);
        return SendAsync<List<LoopIterationRunDto>>(
            settings,
            HttpMethod.Get,
            $"api/v1/runs/{Uri.EscapeDataString(workflowRunId)}/loops/" +
            $"{Uri.EscapeDataString(loopRunId)}/iterations",
            query: query,
            cancellationToken: cancellationToken);
    }

    public Task<ApiResponseEnvelope<List<LoopIterationNodeRunDto>>> ListLoopIterationNodeRunsAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        string loopRunId,
        string loopIterationId,
        CancellationToken cancellationToken = default)
    {
        return SendAsync<List<LoopIterationNodeRunDto>>(
            settings,
            HttpMethod.Get,
            BuildLoopIterationPath(workflowRunId, loopRunId, loopIterationId, "nodes"),
            cancellationToken: cancellationToken);
    }

    public Task<ApiResponseEnvelope<List<LoopIterationTableRefDto>>> ListLoopIterationTableRefsAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        string loopRunId,
        string loopIterationId,
        string? role = null,
        CancellationToken cancellationToken = default)
    {
        var query = string.IsNullOrWhiteSpace(role)
            ? null
            : new[] { new KeyValuePair<string, string?>("role", role) };
        return SendAsync<List<LoopIterationTableRefDto>>(
            settings,
            HttpMethod.Get,
            BuildLoopIterationPath(workflowRunId, loopRunId, loopIterationId, "table-refs"),
            query: query,
            cancellationToken: cancellationToken);
    }

    public Task<ApiResponseEnvelope<WorkflowRunDto>> RetryWorkflowRunAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        string? triggerSource = null,
        CancellationToken cancellationToken = default)
    {
        Dictionary<string, string?>? payload = null;
        if (!string.IsNullOrWhiteSpace(triggerSource))
        {
            payload = new Dictionary<string, string?>
            {
                ["trigger_source"] = triggerSource,
            };
        }

        return SendAsync<WorkflowRunDto>(
            settings,
            HttpMethod.Post,
            $"api/v1/runs/{Uri.EscapeDataString(workflowRunId)}/retry",
            payload: payload,
            cancellationToken: cancellationToken);
    }

    public Task<ApiResponseEnvelope<RunTableCleanupResultDto>> CleanupRunTableRefsAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        CancellationToken cancellationToken = default)
    {
        return CleanupRunTableRefsBatchAsync(
            settings,
            workflowRunId,
            maxRefs: 100,
            timeBudgetMs: 1000,
            cancellationToken: cancellationToken);
    }

    public Task<ApiResponseEnvelope<RunTableCleanupResultDto>> CleanupRunTableRefsBatchAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        int maxRefs,
        int timeBudgetMs,
        string? cursor = null,
        CancellationToken cancellationToken = default)
    {
        var query = new List<KeyValuePair<string, string?>>
        {
            new("max_refs", maxRefs.ToString()),
            new("time_budget_ms", timeBudgetMs.ToString()),
        };
        if (!string.IsNullOrWhiteSpace(cursor))
        {
            query.Add(new KeyValuePair<string, string?>("cursor", cursor));
        }

        return SendAsync<RunTableCleanupResultDto>(
            settings,
            HttpMethod.Delete,
            $"api/v1/runs/{Uri.EscapeDataString(workflowRunId)}/table-refs",
            query: query,
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

    public Task<ApiResponseEnvelope<SharedPublicationCatalogPageDto>> ListSharedPublicationCatalogAsync(
        EngineHostConnectionSettings settings,
        string? query = null,
        int offset = 0,
        int limit = 50,
        CancellationToken cancellationToken = default)
    {
        var queryValues = new List<KeyValuePair<string, string?>>
        {
            new("query", query),
            new("offset", offset.ToString()),
            new("limit", limit.ToString()),
        };

        return SendAsync<SharedPublicationCatalogPageDto>(
            settings,
            HttpMethod.Get,
            "api/v1/shared-publications/catalog",
            query: queryValues,
            cancellationToken: cancellationToken);
    }

    public Task<ApiResponseEnvelope<SharedPublicationSummaryPageDto>> ListSharedPublicationVersionSummariesAsync(
        EngineHostConnectionSettings settings,
        string shareName,
        int offset = 0,
        int limit = 50,
        CancellationToken cancellationToken = default)
    {
        var query = new List<KeyValuePair<string, string?>>
        {
            new("paged", "true"),
            new("offset", offset.ToString()),
            new("limit", limit.ToString()),
        };

        return SendAsync<SharedPublicationSummaryPageDto>(
            settings,
            HttpMethod.Get,
            $"api/v1/shared-publications/{Uri.EscapeDataString(shareName)}/versions",
            query: query,
            cancellationToken: cancellationToken);
    }

    public Task<ApiResponseEnvelope<SharedPublicationMemberPageDto>> ListSharedPublicationMembersAsync(
        EngineHostConnectionSettings settings,
        string publicationId,
        int offset = 0,
        int limit = 100,
        CancellationToken cancellationToken = default)
    {
        var query = new List<KeyValuePair<string, string?>>
        {
            new("offset", offset.ToString()),
            new("limit", limit.ToString()),
        };

        return SendAsync<SharedPublicationMemberPageDto>(
            settings,
            HttpMethod.Get,
            $"api/v1/shared-publications/{Uri.EscapeDataString(publicationId)}/members",
            query: query,
            cancellationToken: cancellationToken);
    }

    public Task<ApiResponseEnvelope<SharedPublicationCleanupPreviewDto>> GetSharedPublicationCleanupPreviewAsync(
        EngineHostConnectionSettings settings,
        string publicationId,
        CancellationToken cancellationToken = default)
    {
        return SendAsync<SharedPublicationCleanupPreviewDto>(
            settings,
            HttpMethod.Get,
            $"api/v1/shared-publications/{Uri.EscapeDataString(publicationId)}/cleanup-preview",
            cancellationToken: cancellationToken);
    }

    public Task<ApiResponseEnvelope<SharedPublicationCleanupResultDto>> CleanupSharedPublicationAsync(
        EngineHostConnectionSettings settings,
        string publicationId,
        CancellationToken cancellationToken = default)
    {
        return SendAsync<SharedPublicationCleanupResultDto>(
            settings,
            HttpMethod.Post,
            $"api/v1/shared-publications/{Uri.EscapeDataString(publicationId)}/cleanup",
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

    private static List<KeyValuePair<string, string?>> BuildPagedStatusQuery(
        int offset,
        int limit,
        IReadOnlyCollection<string>? statuses)
    {
        var query = new List<KeyValuePair<string, string?>>
        {
            new("offset", offset.ToString()),
            new("limit", limit.ToString()),
        };
        if (statuses is not null)
        {
            query.AddRange(statuses.Select(status => new KeyValuePair<string, string?>("status", status)));
        }

        return query;
    }

    private static string BuildLoopIterationPath(
        string workflowRunId,
        string loopRunId,
        string loopIterationId,
        string suffix)
    {
        return $"api/v1/runs/{Uri.EscapeDataString(workflowRunId)}/loops/" +
               $"{Uri.EscapeDataString(loopRunId)}/iterations/" +
               $"{Uri.EscapeDataString(loopIterationId)}/{suffix}";
    }
}
