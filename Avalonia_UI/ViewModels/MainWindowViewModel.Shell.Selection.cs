using System;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void SynchronizeSelectedShellPageIndex(ShellPageKey key)
    {
        var index = GetShellNavigationItemIndex(key);
        if (SelectedShellPageIndex == index)
        {
            return;
        }

        isSynchronizingShellSelection = true;
        try
        {
            SelectedShellPageIndex = index;
        }
        finally
        {
            isSynchronizingShellSelection = false;
        }
    }

    private void SynchronizeSelectedShellPageKey(int index)
    {
        var key = ShellNavigationItems[index].Key;
        if (SelectedShellPageKey == key)
        {
            return;
        }

        isSynchronizingShellSelection = true;
        try
        {
            SelectedShellPageKey = key;
        }
        finally
        {
            isSynchronizingShellSelection = false;
        }
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
