using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Models;

namespace Avalonia_UI.Services;

public interface IRunTableDirectoryService
{
    Task<ApiResponseEnvelope<NodeRunPageDto>> ListNodeRunsAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        int offset = 0,
        int limit = 100,
        IReadOnlyCollection<string>? statuses = null,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<RunTableDirectoryPageDto>> ListTableRefsAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        int offset = 0,
        int limit = 100,
        string? nodeRunId = null,
        string? tableType = null,
        IReadOnlyCollection<string>? lifecycleStatuses = null,
        string? logicalTableId = null,
        CancellationToken cancellationToken = default);
}
