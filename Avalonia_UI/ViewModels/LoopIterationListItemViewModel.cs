using Avalonia_UI.Api;

namespace Avalonia_UI.ViewModels;

public sealed class LoopIterationListItemViewModel
{
    public LoopIterationListItemViewModel(LoopIterationRunDto iteration)
    {
        LoopIterationId = iteration.LoopIterationId;
        LoopRunId = iteration.LoopRunId;
        IterationIndex = iteration.IterationIndex;
        Status = iteration.Status;
        InputTableRefId = iteration.InputTableRefId;
        OutputTableRefId = iteration.OutputTableRefId;
        FailedNodeRunId = iteration.FailedNodeRunId;
    }

    public string LoopIterationId { get; }

    public string LoopRunId { get; }

    public int IterationIndex { get; }

    public string Status { get; }

    public string? InputTableRefId { get; }

    public string? OutputTableRefId { get; }

    public string? FailedNodeRunId { get; }

    public string IndexText => $"#{IterationIndex + 1}";
}
