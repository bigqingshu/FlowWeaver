using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Models;

namespace Avalonia_UI.Services;

public sealed class RunTableDirectoryService : IRunTableDirectoryService
{
    private readonly IEngineHostApiClient _apiClient;

    public RunTableDirectoryService(IEngineHostApiClient apiClient)
    {
        _apiClient = apiClient;
    }

    public Task<ApiResponseEnvelope<NodeRunPageDto>> ListNodeRunsAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        int offset = 0,
        int limit = 100,
        IReadOnlyCollection<string>? statuses = null,
        CancellationToken cancellationToken = default)
    {
        return _apiClient.ListNodeRunsPageAsync(
            settings,
            workflowRunId,
            offset,
            limit,
            statuses,
            cancellationToken);
    }

    public Task<ApiResponseEnvelope<RunTableDirectoryPageDto>> ListTableRefsAsync(
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
        return _apiClient.ListRunTableDirectoryAsync(
            settings,
            workflowRunId,
            offset,
            limit,
            nodeRunId,
            tableType,
            lifecycleStatuses,
            logicalTableId,
            cancellationToken);
    }
}
