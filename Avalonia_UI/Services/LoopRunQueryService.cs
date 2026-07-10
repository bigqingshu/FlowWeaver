using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Models;

namespace Avalonia_UI.Services;

public sealed class LoopRunQueryService : ILoopRunQueryService
{
    private readonly IEngineHostApiClient _apiClient;

    public LoopRunQueryService(IEngineHostApiClient apiClient)
    {
        _apiClient = apiClient;
    }

    public Task<ApiResponseEnvelope<List<LoopRunDto>>> ListLoopsAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        int offset = 0,
        int limit = 50,
        IReadOnlyCollection<string>? statuses = null,
        CancellationToken cancellationToken = default)
    {
        return _apiClient.ListLoopRunsAsync(
            settings,
            workflowRunId,
            offset,
            limit,
            statuses,
            cancellationToken);
    }

    public Task<ApiResponseEnvelope<List<LoopIterationRunDto>>> ListIterationsAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        string loopRunId,
        int offset = 0,
        int limit = 50,
        IReadOnlyCollection<string>? statuses = null,
        CancellationToken cancellationToken = default)
    {
        return _apiClient.ListLoopIterationsAsync(
            settings,
            workflowRunId,
            loopRunId,
            offset,
            limit,
            statuses,
            cancellationToken);
    }

    public Task<ApiResponseEnvelope<List<LoopIterationNodeRunDto>>> ListIterationNodesAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        string loopRunId,
        string loopIterationId,
        CancellationToken cancellationToken = default)
    {
        return _apiClient.ListLoopIterationNodeRunsAsync(
            settings,
            workflowRunId,
            loopRunId,
            loopIterationId,
            cancellationToken);
    }

    public Task<ApiResponseEnvelope<List<LoopIterationTableRefDto>>> ListIterationTableRefsAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        string loopRunId,
        string loopIterationId,
        string? role = null,
        CancellationToken cancellationToken = default)
    {
        return _apiClient.ListLoopIterationTableRefsAsync(
            settings,
            workflowRunId,
            loopRunId,
            loopIterationId,
            role,
            cancellationToken);
    }
}
