using System;
using System.Linq;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private static bool IsKnownShellPageKey(ShellPageKey key)
    {
        return BuiltinShellPages.All.Any(page => page.Key == key);
    }

    private bool IsKnownShellPageIndex(int index)
    {
        return index >= 0 && index < ShellNavigationItems.Count;
    }

    partial void OnSelectedShellPageKeyChanging(ShellPageKey value)
    {
        if (!IsKnownShellPageKey(value))
        {
            throw new InvalidOperationException($"Unknown shell page key '{value}'.");
        }
    }

    partial void OnSelectedShellPageKeyChanged(ShellPageKey value)
    {
        if (!isSynchronizingShellSelection)
        {
            SynchronizeSelectedShellPageIndex(value);
        }

        OnPropertyChanged(nameof(SelectedShellNavigationItem));
        OnPropertyChanged(nameof(SelectedShellPageContentKey));
        LoadSelectedDataPreviewTableCommand.NotifyCanExecuteChanged();
    }

    partial void OnSelectedShellPageIndexChanging(int value)
    {
        if (!IsKnownShellPageIndex(value))
        {
            throw new InvalidOperationException($"Unknown shell page index '{value}'.");
        }
    }

    partial void OnSelectedShellPageIndexChanged(int value)
    {
        if (!isSynchronizingShellSelection)
        {
            SynchronizeSelectedShellPageKey(value);
        }
    }
}
