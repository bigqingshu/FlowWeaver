using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Models;

namespace Avalonia_UI.Services;

public interface IWorkflowRunRuntimeOptionsService
{
    Task<ApiResponseEnvelope<WorkflowRunRuntimeOptionsDto>> GetAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<WorkflowRunRuntimeOptionsDto>> ReplaceAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        int expectedVersion,
        WorkflowRunRuntimeOptionsOverlayDto overlay,
        CancellationToken cancellationToken = default);
}

public sealed class WorkflowRunRuntimeOptionsService : IWorkflowRunRuntimeOptionsService
{
    private readonly IEngineHostApiClient apiClient;

    public WorkflowRunRuntimeOptionsService(IEngineHostApiClient apiClient)
    {
        this.apiClient = apiClient;
    }

    public Task<ApiResponseEnvelope<WorkflowRunRuntimeOptionsDto>> GetAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        CancellationToken cancellationToken = default)
    {
        return apiClient.GetRunRuntimeOptionsAsync(
            settings,
            workflowRunId,
            cancellationToken);
    }

    public Task<ApiResponseEnvelope<WorkflowRunRuntimeOptionsDto>> ReplaceAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        int expectedVersion,
        WorkflowRunRuntimeOptionsOverlayDto overlay,
        CancellationToken cancellationToken = default)
    {
        return apiClient.ReplaceRunRuntimeOptionsAsync(
            settings,
            workflowRunId,
            expectedVersion,
            overlay,
            cancellationToken);
    }
}
