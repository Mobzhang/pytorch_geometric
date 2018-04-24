import os

import torch
from torch_geometric.data import InMemoryDataset, collate_to_set, split_set
from torch_geometric.read import parse_sdf
from torch_geometric.datasets.utils.download import download_url
from torch_geometric.datasets.utils.extract import extract_tar
from torch_geometric.datasets.utils.spinner import Spinner


class QM9(InMemoryDataset):
    num_graphs = 130831
    data_url = 'http://deepchem.io.s3-website-us-west-1.amazonaws.com/' \
               'datasets/gdb9.tar.gz'
    mask_url = 'https://ndownloader.figshare.com/files/3195404'

    def __init__(self, root, split, transform=None):
        super(QM9, self).__init__(root, transform)

        filename = self._processed_files[0]
        dataset, slices = torch.load(filename)
        self.dataset, self.slices = split_set(dataset, slices, split)

    @property
    def raw_files(self):
        return 'gdb9.sdf', 'gdb9.sdf.csv', '3195404'

    @property
    def processed_files(self):
        return 'data.pt'

    def download(self):
        file_path = download_url(self.data_url, self.raw_dir)
        extract_tar(file_path, self.raw_dir, mode='r')
        os.unlink(file_path)
        download_url(self.mask_url, self.raw_dir)

    def process(self):
        spinner = Spinner('Processing').start()

        # Parse *.sdf to data list.
        with open(self._raw_files[0], 'r') as f:
            src = f.read().split('$$$$\n')[:-1]
            src = [x.split('\n')[3:-2] for x in src]
            data_list = [parse_sdf(x) for x in src]
        dataset, slices = collate_to_set(data_list)

        # Add targets to dataset.
        with open(self._raw_files[1], 'r') as f:
            src = [x.split(',')[4:16] for x in f.read().split('\n')[1:-1]]
            y = torch.Tensor([[float(y) for y in x] for x in src])
            dataset.y = y
            slices['y'] = torch.arange(y.size(0) + 1, out=torch.LongTensor())

        # Remove invalid data.
        with open(self._raw_files[2], 'r') as f:
            src = f.read().split('\n')[9:-2]
            src = torch.LongTensor([int(x.split()[0]) for x in src])
            split = torch.arange(y.size(0), out=torch.LongTensor())
            split = split[split == split.clone().index_fill_(0, src, -1)]

        dataset, slices = split_set(dataset, slices, split)
        torch.save((dataset, slices), self._processed_files[0])

        spinner.success()
