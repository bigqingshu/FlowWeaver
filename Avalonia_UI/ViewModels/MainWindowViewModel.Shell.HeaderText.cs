using System;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private string ResolveShellPageHeaderText(ShellPageDescriptor descriptor)
    {
        return descriptor.HeaderPropertyName switch
        {
            nameof(WorkflowsSectionText) => WorkflowsSectionText,
            nameof(DataPreviewTabText) => DataPreviewTabText,
            nameof(RunsSectionText) => RunsSectionText,
            nameof(DataTabText) => DataTabText,
            nameof(LogsTabText) => LogsTabText,
            nameof(SettingsMenuText) => SettingsMenuText,
            _ => throw new InvalidOperationException(
                $"Unknown shell page header property '{descriptor.HeaderPropertyName}'."),
        };
    }
}
