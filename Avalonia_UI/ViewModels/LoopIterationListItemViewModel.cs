using Avalonia_UI.Api;
using Avalonia_UI.Localization;

namespace Avalonia_UI.ViewModels;

public sealed class LoopIterationListItemViewModel : ViewModelBase
{
    private readonly DisplayTextFormatter displayTextFormatter;

    public LoopIterationListItemViewModel(
        LoopIterationRunDto iteration,
        DisplayTextFormatter? displayTextFormatter = null)
    {
        this.displayTextFormatter = displayTextFormatter ?? DisplayTextFormatter.Invariant;
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

    public string StatusText => displayTextFormatter.FormatRuntimeStatus(Status);

    public void RefreshLocalizedText()
    {
        OnPropertyChanged(nameof(StatusText));
    }
}
