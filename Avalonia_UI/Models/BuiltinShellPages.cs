using System.Collections.Generic;
using Avalonia_UI.ViewModels;
using Avalonia_UI.Views.Pages;

namespace Avalonia_UI.Models;

public static class BuiltinShellPages
{
    public static IReadOnlyList<ShellPageDescriptor> All { get; } =
        new[]
        {
            new ShellPageDescriptor(
                ShellPageKey.Workflows,
                ShellPageContentKey.Workflows,
                10,
                nameof(MainWindowViewModel.WorkflowsSectionText),
                typeof(WorkflowPage).FullName!),
            new ShellPageDescriptor(
                ShellPageKey.Runs,
                ShellPageContentKey.Runs,
                20,
                nameof(MainWindowViewModel.RunsSectionText),
                typeof(RunMonitorPage).FullName!),
            new ShellPageDescriptor(
                ShellPageKey.Data,
                ShellPageContentKey.Data,
                30,
                nameof(MainWindowViewModel.DataTabText),
                typeof(DataPage).FullName!),
            new ShellPageDescriptor(
                ShellPageKey.Logs,
                ShellPageContentKey.Logs,
                40,
                nameof(MainWindowViewModel.LogsTabText),
                typeof(LogsAuditPage).FullName!),
            new ShellPageDescriptor(
                ShellPageKey.Settings,
                ShellPageContentKey.Settings,
                50,
                nameof(MainWindowViewModel.SettingsMenuText),
                typeof(SettingsPage).FullName!),
        };
}
