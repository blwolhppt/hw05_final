from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Post, Group, User
from django.db.models.fields.files import ImageFieldFile


class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание'
        )
        cls.post_0 = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post(self):
        """Валидная форма создает запись в create_post."""

        form_data = {
            'text': 'Тестовый пост',
            'group': self.group.id,
        }

        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )

        self.assertRedirects(response,
                             reverse('posts:profile',
                                     kwargs={'username': self.user.username}))

        self.assertTrue(Post.objects.filter(text='Тестовый пост',
                                            author=self.user,
                                            group=self.group).exists())

    def test_create_post_with_picture(self):
        """Валидная форма создает запись в create_post с картинкой."""
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )

        form_data = {
            'text': 'Тестовый пост(картинка)',
            'group': self.group.id,
            'image': uploaded.name,
        }
        #print(uploaded.name)
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )

        self.assertRedirects(response,
                             reverse('posts:profile',
                                     kwargs={'username': self.user.username}))
        #print(form_data)
        self.assertTrue(Post.objects.filter(text='Тестовый пост(картинка)',
                                            author=self.user,
                                            group=self.group).exists())

    def test_edit_post(self):
        """Валидная форма изменяет запись в edit_post."""
        form_data = {
            'text': 'Новый Тестовый пост',
            'group': self.group.id
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={
                'post_id': self.post_0.id}),
            data=form_data,
            follow=True)
        modified_post = Post.objects.get(id=self.post_0.id)
        self.assertRedirects(response, reverse('posts:post_detail', args=(1,)))
        self.assertNotEqual(modified_post.text, self.post_0.text)

    def test_edit_post_invalid(self):
        """Проверка на невалидные данные."""
        form_data = {
            'text': ' ',
        }
        self.authorized_client.post(
            reverse('posts:post_edit', args=f'{self.post_0.id}'),
            data=form_data,
            follow=True)
        self.assertFalse(Post.objects.filter(text='').exists())

    def test_guest_cannot_edit_post(self):
        """Проверка edit_post для guest_client."""
        form_data = {
            "text": "Тестовый пост(guest)",
            "group": self.group.id
        }
        response = self.guest_client.post(
            reverse("posts:post_edit", kwargs=({"post_id": self.post_0.id})),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response, f"/posts/{self.post_0.id}/"
        )

    def test_guest_cannot_create(self):
        """Проверка create_post для guest_client."""
        form_data = {
            "text": "Тестовый пост (guest)",
            "group": self.group.id
        }
        response = self.guest_client.post(
            reverse("posts:post_create"),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response, "/auth/login/?next=/create/"
        )
