using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Models;

namespace Avalonia_UI.Services;

public interface ILoopRunQueryService
{
    Task<ApiResponseEnvelope<List<LoopRunDto>>> ListLoopsAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        int offset = 0,
        int limit = 50,
        IReadOnlyCollection<string>? statuses = null,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<List<LoopIterationRunDto>>> ListIterationsAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        string loopRunId,
        int offset = 0,
        int limit = 50,
        IReadOnlyCollection<string>? statuses = null,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<List<LoopIterationNodeRunDto>>> ListIterationNodesAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        string loopRunId,
        string loopIterationId,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<List<LoopIterationTableRefDto>>> ListIterationTableRefsAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        string loopRunId,
        string loopIterationId,
        string? role = null,
        CancellationToken cancellationToken = default);
}
